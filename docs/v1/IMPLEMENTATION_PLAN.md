# TraceRelay v1 精简实现方案

状态：依据 `REQUIREMENTS.md` 的实现候选。目标是先完成一条简单、可故障验证的闭环。

## 1. 架构

运行时只包含两个进程：

```text
CLI
 └─ 启动/查询/注册
        |
        v
Supervisor  <----心跳管道---->  Relay Service
                                  ├─ 本地控制端口
                                  ├─ 单应用会话、多连接 TCP 代理
                                  └─ 证据写入

离线命令：verify <session_dir>
```

- `Supervisor` 是后台主进程，只负责启动并监测 `Relay Service`、保存运行状态和在 Service 异常退出时写报警。
- `Relay Service` 负责控制接口、单会话状态、代理、日志和反向监测 Supervisor。
- `verify` 不连接运行时，只读会话目录。
- TraceRelay 不创建或控制任何被代理应用或上游应用。

不引入 Coordinator、通用 Worker 框架、消息总线、数据库、共享内存或原生扩展。

## 2. 技术选择

| 问题 | 选择 |
|---|---|
| 语言 | CPython 3.13 |
| 运行平台 | Windows 11 x64 |
| 运行时依赖 | Python 标准库 |
| 控制接口 | 默认 `127.0.0.1:43190`；长度受限的单行 JSON 请求/响应 |
| 数据接口 | 每次注册分配一个临时 `127.0.0.1` TCP 监听端口 |
| 监控接口 | `multiprocessing.Pipe` 心跳和状态消息 |
| 后台运行 | CLI 以 Windows detached process 启动 Supervisor |
| 证据日志 | 一个固定头部、原始载荷、SHA-256 哈希链的二进制追加文件 |
| 元数据 | 小型 UTF-8 JSON；临时文件写完后 `os.replace` |
| 持久刷新 | 文件 `flush()` 后 `os.fsync()` |
| 并发 | 一个 accept 线程；每个连接两个方向线程；共享日志写锁；不使用异步框架 |
| 测试 | pytest；必要的故障点使用显式注入，不构建通用注入框架 |

选择线程的原因：v1 只有一个本地应用会话；每个连接仍是两个阻塞字节方向；无需引入异步框架或通用 Worker 层。

## 3. 控制模型

CLI 命令保持六个：

| 命令 | 行为 |
|---|---|
| `tracerelay start` | 启动 Supervisor 和 Service；已运行时返回当前状态。 |
| `tracerelay status` | 返回进程、会话和最后报警状态。 |
| `tracerelay register --upstream-port N` | 注册一个会话并返回 `session_id`、代理主机和端口。 |
| `tracerelay close` | 请求结束等待中或运行中的会话；10 秒内静止才正常封口，否则保持不完整。 |
| `tracerelay stop` | 请求结束当前会话并停止两个 TraceRelay 进程；超时返回非零结果。 |
| `tracerelay verify PATH` | 只读校验一个会话目录。 |

控制请求只允许一个 JSON 对象。响应包含 `ok`、`command`、`state`、结果字段或一个简短错误。报警响应只含报警路径，不通过 IPC 传正文。

`start` 先探测固定控制端口：

- 收到有效 TraceRelay 状态则报告已经运行；
- 连接被拒绝则启动 Supervisor，并等待 Service 就绪；
- 端口已被其他协议占用则明确失败。

Service 对控制端口的独占绑定同时充当单实例锁。v1 不保存 PID 文件、端口发现文件或启动身份目录。

由于用户可信且端口只绑定回环地址，v1 不实现控制鉴权。

## 4. 会话状态

只使用五个状态：

```text
IDLE -> WAITING -> CONNECTING -> RELAYING
          ^             |           |
          +-------------+-----------+
          |                         |
          +--- explicit close ---> IDLE
          \------ fatal error ----> FAULT
```

- `register`：`IDLE -> WAITING`。
- 客户端接入：保持监听端口，新增连接进入 `CONNECTING`。
- 上游连接成功：`CONNECTING -> RELAYING`。
- 单个连接正常 EOF：只结束该连接；无其他活动连接时回到 `WAITING`。
- `close` 或 `stop`：停止 accept，等待已接受连接静止，封口后回到 `IDLE`。
- 任意证据、监控或代理致命错误：进入 `FAULT`，报警、断链、退出。
- Service 重启永远从 `IDLE` 开始；旧会话不恢复、不续写。

并发状态按全体连接聚合：存在转发连接时为 `RELAYING`；否则存在建连连接时为 `CONNECTING`；否则为 `WAITING`。状态机不保留应用队列、重试树和恢复分支。

## 5. 证据格式

### 5.1 会话文件

`session.json` 在代理开始监听前创建并刷新。它包含：

- `format_version`
- `session_id`
- `created_at_utc`
- `proxy_host` / `proxy_port`
- `upstream_host` / `upstream_port`
- 本会话实际采用的限制值

`complete.json` 只在日志成功封口后原子创建。没有该文件即不完整。

### 5.2 日志记录

`journal.trr` 使用小端固定头部。头部字段仅包括：

- magic 和版本；
- 记录类型：`DATA`、`SEND_OK`、`SEND_ERROR`；
- 正整数 `connection_id`；
- 方向；
- 全局序号；
- UTC 纳秒和单调时钟纳秒；
- 关联的 `DATA` 序号；
- 方向流偏移；
- 载荷长度；
- 整数结果码；
- 前一记录 SHA-256。

记录尾部保存当前记录 SHA-256。哈希覆盖完整头部和载荷。

处理一个数据块的固定顺序：

1. 写 `DATA`，刷新并 `fsync`。
2. 调用对端 `sendall`。
3. 成功则写并刷新 `SEND_OK`。
4. 失败则尽力写并刷新 `SEND_ERROR`，随后故障退出。

若进程在步骤 2 后、步骤 3 前退出，校验器将对应数据报告为 `UNKNOWN`。系统不猜测实际结果。

每个连接、每个方向维护独立流偏移。日志全局序号只用于确定记录顺序，不声称不同连接或方向在远端的业务先后关系。当前写入格式为 v2；只读校验器继续支持既有单连接 v1 证据。

## 6. 监控和报警

Supervisor 每秒向 Service 发送心跳。Service 每秒回传当前状态和活动会话 ID。

- Service 进程异常退出：Supervisor 写报警文件。
- Supervisor 管道关闭或 5 秒无心跳：Service 写报警文件，关闭套接字并退出。
- Service 内部致命错误：Service 先尝试写报警，再关闭套接字并非零退出。
- 正常 `stop`：双方通过管道确认，不产生故障报警。
- Supervisor 不自动重启 Service；用户必须重新执行 `start`，旧会话保持不完整。

每个报警是一个独立 JSON 文件，包含：

- `incident_id`
- `created_at_utc`
- `source`
- `reason`
- `service_pid` / `supervisor_pid`
- 可用时的 `session_id`
- 异常类型和简短消息

不建立原因码目录、报警队列、第二存储通道或正文 IPC 分片。

## 7. 校验器

校验器按字节独立遍历日志，不调用生产写入路径。

检查顺序：

1. `session.json` 存在且字段有效。
2. 每条完整记录的长度、版本、序号、`connection_id`、方向、连接内偏移和哈希链有效。
3. `SEND_OK` / `SEND_ERROR` 只关联同一连接中已存在的 `DATA`，且一个 `DATA` 最多一个终态。
4. 按连接和方向重建字节流，同时汇总方向计数。
5. `complete.json` 存在时，最终序号、哈希和计数必须完全匹配。

结果：

- `VALID_COMPLETE`：日志完整，完成标记匹配，无未知发送结果。
- `VALID_INCOMPLETE`：完整前缀可信，但没有完成标记、尾部残缺或存在未知发送结果。
- `INVALID`：中部损坏、哈希错误、序号/偏移错误、非法关联或伪造完成标记。

校验器不修复、不重命名、不追加任何会话文件。
`VALID_COMPLETE` 只描述证据封口状态，不等同于被代理应用的任务成功。

## 8. 源码范围

预期生产文件保持在十个以内：

```text
src/tracerelay/
  __init__.py
  __main__.py
  cli.py
  config.py
  control.py
  journal.py
  session.py
  service.py
  supervisor.py
  verify.py
```

测试文件按行为划分：

```text
tests/
  test_config.py
  test_journal.py
  test_control.py
  test_relay.py
  test_multiconnection.py
  test_monitoring.py
  test_cli.py
```

只有出现循环依赖或单文件明显失控时才拆文件；不得提前创建抽象层。

## 9. 实现顺序

### M0：清理旧基线

状态：已完成。

1. 删除包内旧高保证契约副本、旧构建身份和旧源文件占位清单。
2. 删除只验证旧契约快照的测试。
3. 更新包配置和入口点。

验收：包可导入；旧方案不参与构建；测试发现不再引用旧批次或旧格式。

### M1：最短可运行闭环

状态：已完成。

1. 实现配置、路径和原子 JSON 写入。
2. 实现日志写入器和独立校验器。
3. 实现前台 Service：`register`、应用会话、上游连接、双向转发、显式正常封口。
4. 实现 `status`、`register`、`close`、`verify` CLI。

验收：前台模式下完成一次随机二进制双向通信；日志可重建；校验结果为 `VALID_COMPLETE`。

这是第一个必须停下检查的稳定点。M1 不依赖后台进程和故障监控。

### M2：故障闭环

状态：已完成。

1. 实现 detached Supervisor 和 `start` / `stop`。
2. 实现双向心跳、报警文件和固定控制端口冲突处理。
3. 实现进程终止、日志写失败、上游失败和监控失联测试。

验收：Service 或 Supervisor 单独故障时，另一方在 5 秒内执行规定动作；未刷新数据不转发；已有日志仍可校验。

### M3：边界和交付

状态：已完成。

1. 实现日志限额和准入空间检查。
2. 完成第二会话、顺序/并发连接、截断、篡改和重启测试。
3. 完成 Windows wheel 安装、CLI 冒烟和全套测试。
4. 删除实现过程中发现但未使用的代码和配置。

验收：`REQUIREMENTS.md` 第 8 节全部通过，并保存命令、退出码和测试结果。

## 10. 工作分配原则

v1 的控制、状态、代理和日志顺序强耦合，默认由同一个实现 Agent 连续完成 M0 至 M2。

只有日志字节格式冻结后，离线校验测试或 Windows 黑盒故障测试才具备无歧义边界，可以交给独立 subagent。subagent 不得修改生产实现，不得继续派生任务，也不得使用任何 Aegis 相关 skill。

每个里程碑统一完成、统一测试后再审查。禁止发现一个问题就立即改一次、立即开启下一轮。

## 11. 预计工作量

| 里程碑 | 聚焦工时 |
|---|---:|
| M0 | 已完成 |
| M1 | 3–5 小时 |
| M2 | 3–5 小时 |
| M3 | 3–5 小时 |
| 剩余 | 9–15 小时 |

估算包含实现、自动化测试和一次统一修订，不包含新增范围。M1 预计半个工作日内形成可运行闭环。

## 12. 范围控制

- 只实现需求文档中明确列出的行为。
- 新发现的非阻塞问题进入后续事项，不在 v1 处理。
- 阻塞项若要求增加进程、协议、持久格式或支持场景，先暂停并由用户决定。
- 不以性能优化、安全加固、未来兼容或架构美观为理由扩大当前实现。
