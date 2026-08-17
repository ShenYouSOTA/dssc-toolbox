# DSSC-Toolbox

Data Space Support Centre (DSSC) 工具链研究仓库，围绕统一场景 **Building Energy Consumption Data Product** 对四类数据空间工具进行调研、部署与集成验证。

## 研究范围

本仓库按四个研究方向组织：

| 组 | 方向 | 核心工具 | 仓库位置 |
|---|---|---|---|
| A 组 | Data Exchange / Connector | FIWARE Data Space Connector (FIWARE DSC) | `demo/`, `data-space-connector/`, `justfile` |
| B 组 | Trust / Compliance | Gaia-X Compliance Service + Registry | `wiki/20-gaia-x-xin-ren-kuang-jia-ji-cheng.md`, `DSSC_Tool_Learning/` |
| C 组 | Semantic Model Governance | Semantic Treehouse | `wiki/` 相关文档, `DSSC_Tool_Learning/` |
| D 组 | Conformance / Validation | Interoperability Test Bed (ITB) + SEMIC SHACL Validator | `wiki/` 相关文档, `DSSC_Tool_Learning/` |

当前 A 组已完成可运行 Demo 和 k3s 本地部署记录；B/C/D 组主要沉淀在 Wiki 与学习资料中。

## 统一研究场景

场景：建筑小时级能耗数据产品发布与消费。

- Provider：Energy Data Provider Ltd.
- Consumer：City Analytics Lab.
- Data Space Authority：City Energy Data Space Authority.
- 数据产品：Building Energy Consumption Dataset API (`building-energy-hourly-v1`).

## 重要通知

### 仓库已更名（2026-08-17）

仓库由 `DSSC-Toolbox` 更名为小写 `dssc-toolbox`（GitHub Pages 路径大小写敏感，did:web 规范要求全小写）。旧地址自动重定向，但本地 clone 请更新 remote：

```bash
git remote set-url origin https://github.com/ShenYouSOTA/dssc-toolbox.git
```

### 全组定稿身份（2026-08-17）

跨组凭证签发/验签统一使用以下签名身份：

| 项 | 值 |
|---|---|
| DID | `did:web:shenyousota.github.io:dssc-toolbox` |
| kid | `did:web:shenyousota.github.io:dssc-toolbox#key-1` |
| 算法 | ES256（EC P-256） |
| did.json | https://shenyousota.github.io/dssc-toolbox/did.json （公网可解析） |
| 密钥 | `demo/data/keys/`（demo 专用私钥已提交，虚构主体，非生产用途） |
| 校验 | `just did-verify`（校验公网 did.json 与本地私钥匹配） |

其他已定稿项：VC Data Model **2.0**（用 `validFrom/validUntil`，不用 `issuanceDate`）、Gaia-X context `https://w3id.org/gaia-x/development#`、legalName `Energy Data Provider Ltd.`、LRN `DEMO-ENERGY-001`、地址 CN / CN-GD、有效期 2026-08-16 ~ 2027-08-16。

语义模型（C 组交接，`C_Semantic_Treehouse/handoff/handoff-to-A-offering-metadata.md` 为机器真源）：

| 项 | 值 |
|---|---|
| 模型版本 | **v0.4**（v0.3→v0.4 为 wire-profile-breaking，勿再用 v0.3） |
| `ex:` namespace | `https://example.org/dssc-energy#` |
| 版本身份 | `https://w3id.org/dssc-demo/building-energy/v0.4` |
| Dataset canonical URI | `https://example.org/dssc-energy/datasets/building-energy-hourly-v1` |
| 数据格式 `dct:format` | `application/json`（精确值，大小写敏感） |
| metadata 序列化 | `application/ld+json` |

A 组 demo metadata 已按 v0.4 字段合同（D04-R001~R017）迁移，并用 C 组官方 v0.4 SHACL shapes 验证通过（valid 0 warning / invalid 4 violations 符合预期）。

### 跨组 API 检测说明（nip.io 机制）

`scorpio-provider.127.0.0.1.nip.io` 等 `*.127.0.0.1.nip.io` 域名解析到**调用者自己的** 127.0.0.1，这是设计如此。任何组员做 API 检测的方式：clone 仓库 → `just up` 本地起 k3s → demo 自动 port-forward，该域名即指向其本机集群，无需改 hosts 或任何配置。

注意：`data-space-connector/` 目录在 `.gitignore` 中未入库，集群部署 yaml 需单独向 A 组索取（后续计划将 `k3s/` 配置移出 ignore）。

场景包位于 `DSSC_Tool_Learning/DSSC_Minimal_Energy_Scenario/`，包含：

- 数据 payload：`data/building-energy-sample.json`
- JSON-LD metadata：`metadata/data-product-valid.jsonld`、`metadata/data-product-invalid.jsonld`
- OpenAPI 合同：`mock-api/openapi.yaml`
- SHACL shapes：`shapes/building-energy-shapes.ttl`
- Gaia-X 模板：`gaia-x/*.template.jsonld`

## 运行环境选择

本仓库支持三条主流运行路径，分别对应 Linux、macOS 与 Windows + WSL2 Ubuntu。

### Linux（推荐）

- 使用 `just up` 一键部署 k3s + FIWARE DSC。
- 首次部署约 15–25 分钟，推荐配置 ≥ 8 核 CPU / 32 GB 内存。
- 详见 `docs/A_fiware_deployment_notes.md` 与 `demo/README.md`。

### macOS

macOS 用户可通过 Docker Desktop 运行完整 k3s 部署，但 Apple Silicon 虚拟化开销较大，且国内网络环境下 Docker Hub / quay.io 官方镜像可能拉取超时。因此建议：

- Docker Desktop 内存建议 ≥ 16 GB，启用 Apple Virtualization framework。
- 资源受限或网络不稳定时，使用 `demo/README.md` 中介绍的轻量白盒 Connector 方案，无需 Kubernetes 即可本地运行。

### Windows + WSL2 Ubuntu（完整部署）

Windows 用户可通过 Docker Desktop + WSL2 Ubuntu 部署完整 FIWARE DSC k3s 环境：

- 包含完整的官方组件：Scorpio、APISIX、OPA、ODRL-PAP、VCVerifier、TMForum API、Contract Management 等。
- 服务入口使用 `*.127.0.0.1.nip.io:8443`。
- 完整 Demo 覆盖 Provider 上传数据、发布 Offering、Consumer OID4VP 认证、受保护数据下载。
- 详见 GitHub 分支 [`feature/ytt-full-data-space-demo`](https://github.com/ShenYouSOTA/dssc-toolbox/tree/feature/ytt-full-data-space-demo)。

## 快速开始

### 1. Mock Demo（无需 Kubernetes）

纯 Python 模拟 Provider/Consumer 数据交换流程，包含认证、目录发现、合同协商、数据传输、数据获取。

```bash
cd demo
uv run python run_demo.py
```

或使用 just：

```bash
just demo-python
```

### 2. 真实集群 Demo（需要 k3s + Helm）

一键启动 k3s、基础设施与 FIWARE DSC 应用组件，并运行完整数据交换流程：

```bash
just up
just demo-cluster
```

注意：首次部署约 15-25 分钟，且当前仍需若干手动补丁（CA issuer、MongoDB ServiceAccount、keystore Secret 等）。建议按 `docs/A_fiware_deployment_notes.md` 分步操作，而非直接一键运行。

## 目录结构

```
dssc-toolbox/
├── AGENTS.md                       # Agent 工作范围约定
├── did.json                        # 公网 DID 文档（GitHub Pages 发布，勿手改，用 just did-export 生成）
├── justfile                        # 集群管理、部署、Demo 一键命令
├── README.md                       # 本文件
├── demo/                           # A 组：Python 数据交换演示
│   ├── config.py                   # 集中配置
│   ├── provider_server.py          # FastAPI Mock Provider
│   ├── consumer_client.py          # Consumer 客户端
│   ├── run_demo.py                 # Mock Demo 编排器
│   ├── demo_real_cluster.py        # Real Cluster Demo
│   ├── did_identity.py             # DID 密钥/did.json 管理工具
│   ├── ARCHITECTURE.md             # Demo 架构与通信流程
│   ├── README.md                   # Demo 详细说明
│   ├── data/                       # 演示数据（按 scenario 组织）+ keys/（demo 密钥）
│   └── logs/                       # 运行日志
├── data-space-connector/           # FIWARE DSC 上游 Helm Chart 仓库
│   ├── charts/                     # Helm Umbrella Chart
│   ├── k3s/                        # 本地 k3s 部署配置
│   ├── doc/                        # 官方部署与流程文档
│   ├── it/                         # k3s 集成测试（Maven + Cucumber）
│   └── README.md
├── docs/                           # A 组部署与对比文档
│   ├── A_fiware_deployment_notes.md # 部署笔记与踩坑记录
│   ├── data_exchange_demo.md        # 数据交换 Demo 流程
│   └── compare-TNO-TSG.md           # TNO TSG 对比分析
├── DSSC_Tool_Learning/             # 统一学习资料与研究场景
│   ├── DSSC_Toolbox_Research_Task_Plan.md
│   ├── DSSC_Toolbox_Scenario.md
│   └── DSSC_Minimal_Energy_Scenario/
└── wiki/                           # 项目文档 Wiki（32 篇）
    ├── 1-xiang-mu-gai-shu.md
    ├── 2-kuai-su-bu-shu-zhi-nan.md
    └── ...
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `just default` | 列出所有可用命令 |
| `just demo-python` | 运行 Mock Demo |
| `just demo-client` | 仅运行 Consumer 客户端 |
| `just demo-cluster` | 运行真实集群 Demo |
| `just demo-cluster-health` | 集群健康检查 |
| `just up` | 一键启动 k3s + 基础设施 + 应用 |
| `just down` | 一键停止并清理 |
| `just smoke-test` | 检查所有 Pod 状态 |
| `just pods` | 查看所有 Pod |
| `just did-export` | 由固定公钥生成 did.json（仓库根） |
| `just did-verify` | 校验公网 did.json 与本地私钥匹配 |
| `just did-k8s-secret` | 输出把固定密钥导入 k3s 的命令 |

## 文档索引

### A 组（Connector / Data Exchange）

- `demo/README.md` — Mock Demo 与 Real Cluster Demo 完整说明
- `demo/ARCHITECTURE.md` — 架构与通信流程
- `docs/A_fiware_deployment_notes.md` — k3s 部署笔记与踩坑记录
- `docs/data_exchange_demo.md` — 数据交换 Demo 流程
- `data-space-connector/README.md` — FIWARE DSC 官方说明

### B / C / D 组

- `DSSC_Tool_Learning/DSSC_Toolbox_Scenario.md` — 统一研究场景
- `DSSC_Tool_Learning/DSSC_Toolbox_Research_Task_Plan.md` — 研究任务设计方案
- `wiki/` — 32 篇项目文档，涵盖部署、认证、授权、Marketplace、Gaia-X、OpenTelemetry 等

## 文档查看方式

### 推荐：Obsidian

1. 安装 [Obsidian](https://obsidian.md/)
2. 打开本地文件夹，选择 `wiki/`
3. 支持双向链接与图谱视图

### 替代：Typora / VS Code

- Typora：直接打开 `wiki/` 下任意 `.md` 文件
- VS Code：安装 `Markdown Preview Enhanced` 或 `Markdown All in One` 后预览

## 相关链接

- [FIWARE Data Space Components](https://github.com/FIWARE)
- [Eclipse Dataspace Components](https://eclipse-edc.github.io/docs/)
- [FIWARE DSC 官方文档](https://fiware-dsc.readthedocs.io/)

## 许可证

本仓库为研究学习用途，具体许可证见各子目录文件。
