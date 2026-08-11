# FIWARE DSC 数据空间演示

两种演示模式：**Mock Demo** (纯本地模拟) 和 **Real Cluster Demo** (走真实 k3s 集群)。

## 快速开始

### 前置条件

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) 包管理器
- (可选) Docker + k3s 集群 (仅 Real Cluster Demo)

### Mock Demo (纯本地，不需要集群)

```bash
cd demo
uv run python run_demo.py
```

自动启动 Provider Mock API → Consumer 发现 → 认证 → 协商 → 传输 → 获取数据 → 验证。

### Real Cluster Demo (走真实 k3s 集群)

```bash
# 先确保 k3s 集群已启动并部署完成
just up                      # 一键启动集群 + 部署所有服务（首次约 15-25 分钟）
just demo-cluster            # 运行完整数据交换流程（约 1-2 分钟）
```

通过 nginx-ingress 访问集群中的 Keycloak、TMForum API、Scorpio 等真实服务。

> **注意：** `just up` 当前仍需要若干手动补丁（CA issuer、MongoDB SA/镜像/认证、keystore Secret 等），详见 [部署笔记](./A_fiware_deployment_notes.md) 第 3-4 节。建议按部署笔记分步操作，而非直接一键运行。

## 项目结构

```
demo/
├── config.py              # 集中配置 (JWT, 端口, 路径, 凭证, scenario 选择)
├── provider_server.py     # FastAPI Mock Provider
├── consumer_client.py     # Consumer 客户端
├── run_demo.py            # Mock Demo 编排器
├── demo_real_cluster.py   # Real Cluster Demo
├── data/                  # 演示数据（按 scenario 组织，便于替换为真实数据）
│   └── scenarios/
│       └── DSSC_Minimal_Energy_Scenario/
│           ├── data/               # 数据 payload（静态 JSON / 未来可换 CSV、Parquet）
│           ├── metadata/           # JSON-LD 数据产品元数据
│           ├── mock-api/           # OpenAPI 合同模板
│           ├── shapes/             # SHACL shapes（可选，用于 validation demo）
│           ├── gaia-x/             # Gaia-X credential 模板（可选）
│           ├── README.md           # 场景说明
│           └── VALIDATION_GUIDE.md # 验证指南
├── pyproject.toml         # 依赖管理
├── uv.lock                # 锁定依赖版本
├── ARCHITECTURE.md        # 架构与通信流程文档
└── logs/                  # 运行日志
```

## 两种 Demo 对比

| 维度 | Mock Demo | Real Cluster Demo |
|------|-----------|-------------------|
| 需要 k3s | ❌ | ✅ |
| 认证方式 | 模拟 JWT | 真实 Keycloak OIDC |
| 数据服务 | 本地 JSON 文件（按 scenario 组织） | Scorpio NGSI-LD + TMForum API |
| Offering 创建 | FastAPI 内存 | TMForum ProductCatalog API |
| 数据访问 | 本地 scenario 数据文件 | Scorpio 实体查询 |
| Contract Negotiation | Provider 内存状态机 | 本地 dataclass 模拟 |
| Transfer Process | Provider 内存状态机 | 本地 dataclass 模拟 |
| 用途 | 开发演示、流程理解 | 部署验证、集成测试 |
| 启动命令 | `just demo-python` | `just demo-cluster` |

## macOS 部署说明

macOS 用户有两条路径运行本 Demo。

### 方案一：完整 k3s 部署（与 Linux 一致）

在 macOS 上可通过 Docker Desktop 运行 `just up` 与 `just demo-cluster`。但存在以下差异：

- Docker Desktop 建议启用 Apple Virtualization framework，并分配 ≥ 16 GB 内存。
- Apple Silicon（M1/M2/M3/M4）芯片通过 Rosetta 模拟 x86_64 容器，可能出现内存占用高、启动慢或镜像拉取超时的情况。
- 国内网络环境下 Docker Hub / quay.io 镜像可能超时，建议配置镜像加速器或预先导入。

### 方案二：轻量白盒 Connector（推荐）

当 k3s 资源开销过大或官方镜像无法下载时，可启动伙伴贡献的 Python 轻量 Connector。它使用标准库 `http.server` 实现 Catalogue、Negotiation 状态机与 Authorization 校验，无需 Kubernetes 或 Docker。

> 该方案原始交付报告位于仓库外 `buffer/DSSC-y/FIWARE FDF 数据空间连接器微服务：轻量化白盒全真模拟技术方案与部署交付报告.md`。

假设已将 `connector.py` 放置于 `demo/` 目录，并已将场景文件 `data-product-valid.jsonld` 与 `building-energy-sample.json` 放在 `demo/metadata/` 与 `demo/data/` 下：

```bash
# 启动轻量 Connector
cd demo
python3 connector.py
```

然后在新终端中执行：

```bash
# 1. 发布 Data Offering
curl -X POST http://127.0.0.1:8080/catalogue/v1/offerings \
  -H "Content-Type: application/ld+json" \
  -d @metadata/data-product-valid.jsonld

# 2. 目录发现
curl http://127.0.0.1:8080/catalogue/v1/offerings

# 3. 契约协商
curl -X POST http://127.0.0.1:8080/negotiation/v1/request \
  -H "Content-Type: application/json" \
  -d '{"datasetId":"building-energy-hourly-v1"}'

# 4. 无 Token 访问数据（应返回 401）
curl http://127.0.0.1:8080/data/building-energy-hourly-v1

# 5. 携带 Gaia-X 合规 Token 访问数据
curl http://127.0.0.1:8080/data/building-energy-hourly-v1 \
  -H "Authorization: Bearer GaiaX-Valid-Credential-Token-From-B"
```

## 演示流程

### Mock Demo 流程 (7 步)

```
Provider 发布 Offering (加载 JSON-LD metadata + OpenAPI contract)
    ↓
1. Consumer 发现 Catalog        → GET /api/catalog
2. 查看 Offering 详情           → GET /api/catalog/{id}
3. 认证 (模拟 OID4VP)          → POST /auth/token
4. 合同协商                     → POST /api/contract-negotiations
5. 数据传输                     → POST /api/transfer-processes
6. 获取数据                     → GET /api/energy/buildings/hourly
7. 验证数据格式                 → 内部校验
```

### Real Cluster Demo 流程 (7 步)

```
1. 集群健康检查                 → 7 个 ingress 端点 (Keycloak, TMForum, Scorpio, TIR, TIL, Dashboard)
2. Provider 创建 Data Offering  → Scorpio 创建 NGSI-LD 实体 + TMForum 创建 ProductSpec + ProductOffering
3. Consumer 发现 Catalog       → TMForum GET /productOffering
4. Consumer Keycloak 认证       → OIDC password grant → 获取 access_token
5. Contract Negotiation         → 本地模拟 REQUESTED → CONFIRMED → AGREED 状态流转
6. Transfer Process             → 本地模拟 REQUESTED → STARTED → COMPLETED 状态流转
7. Consumer 获取数据            → Scorpio GET /ngsi-ld/v1/entities/{id}
```

> 详细时序图和代码位置见 [ARCHITECTURE.md](./ARCHITECTURE.md)

## 配置管理

所有配置集中在 `config.py`，支持环境变量覆盖：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `DEMO_JWT_SECRET` | `dssc-demo-secret-key-...` | JWT 签名密钥 |
| `DEMO_MOCK_PORT` | `8000` | Mock 服务端口 |
| `DEMO_SCENARIO` | `DSSC_Minimal_Energy_Scenario` | 当前使用的 scenario 目录名 |
| `DEMO_DATA_FILE` | `building-energy-sample.json` | 默认数据 payload 文件名 |
| `DEMO_METADATA_FILE` | `data-product-valid.jsonld` | 默认 JSON-LD metadata 文件名 |
| `DEMO_OPENAPI_FILE` | `openapi.yaml` | 默认 OpenAPI 合同模板文件名 |
| `DEMO_KC_REALM` | `test-realm` | Keycloak realm |
| `DEMO_KC_USERNAME` | `employee` | Keycloak 用户名 |
| `DEMO_KC_PASSWORD` | `test` | Keycloak 密码 |
| `KUBECONFIG` | `/tmp/k3s.yaml` | k3s kubeconfig 路径 |

## 数据与 scenario 组织

Mock Demo 的数据、metadata、合同模板全部放在 `demo/data/scenarios/<scenario-name>/` 下，使用相对于 `demo/` 目录的路径。这样做的好处：

1. **自包含**：`demo/` 目录可以独立拷贝或测试，不再依赖仓库根目录的 `DSSC_Tool_Learning/`。
2. **易扩展**：新增 scenario 只需新建 `demo/data/scenarios/<new-scenario>/` 目录并放入对应文件，然后通过 `DEMO_SCENARIO=<new-scenario>` 切换。
3. **易替换真实数据**：把真实数据文件放入 `demo/data/scenarios/<scenario>/data/` 并调整 `DEMO_DATA_FILE`，即可让 Provider 加载真实数据而无需改代码。

### 默认 scenario 结构

```
demo/data/scenarios/DSSC_Minimal_Energy_Scenario/
├── data/
│   └── building-energy-sample.json      # 建筑小时级用电量数据
├── metadata/
│   ├── data-product-valid.jsonld        # 合法 metadata（Provider 默认使用）
│   └── data-product-invalid.jsonld      # 故意错误的 metadata（validation demo 使用）
├── mock-api/
│   └── openapi.yaml                     # 数据接口 OpenAPI 合同
├── shapes/
│   └── building-energy-shapes.ttl       # SHACL shapes
├── gaia-x/
│   ├── legal-participant.template.jsonld
│   └── service-offering.template.jsonld
├── README.md
└── VALIDATION_GUIDE.md
```

### 切换 scenario 或数据文件

```bash
# 使用另一个 scenario
cd demo && DEMO_SCENARIO=my-real-data uv run python run_demo.py

# 使用同一 scenario 下的另一个数据文件
cd demo && DEMO_DATA_FILE=real-buildings-2026.json uv run python run_demo.py server
```

## Justfile 快捷命令

```bash
# Mock Demo
just demo-python              # 运行完整 Mock Demo
just demo-run                 # 运行并保存日志
just demo-client              # 仅运行 Consumer
just demo-building BLD-001    # 按建筑 ID 过滤

# Real Cluster Demo
just demo-cluster             # 运行完整集群 Demo (ingress 直连)
just demo-cluster-health      # 仅健康检查

# 完整流程结束后，A→B 结构化交付结果位于 demo/deliverables/

# 集群管理
just up                       # 一键启动: k3s → 基础设施 → 应用 → smoke test
just down                     # 一键停止 (关机前，保留镜像缓存)
just smoke-test               # 快速检查所有 Pod
just pods                     # 查看所有 Pod
just logs-keycloak            # 查看 Keycloak 日志
just releases                 # 查看所有 Helm releases
```

## Real Cluster 服务端点

通过 nginx-ingress 访问，所有域名解析到 `127.0.0.1`：

| 服务 | 端点 | 用途 |
|------|------|------|
| Provider Keycloak | `https://keycloak-provider.127.0.0.1.nip.io` | Provider 认证 |
| Consumer Keycloak | `https://keycloak-consumer.127.0.0.1.nip.io` | Consumer 认证 |
| TMForum API | `https://tm-forum-api.127.0.0.1.nip.io` | ProductCatalog (Offering 管理) |
| Scorpio | `https://scorpio-provider.127.0.0.1.nip.io` | NGSI-LD Context Broker (数据存储) |
| TIR | `https://tir.127.0.0.1.nip.io` | Trusted Issuers Registry (DID 注册) |
| TIL | `https://til-provider.127.0.0.1.nip.io` | Trusted Issuers List |
| Dashboard | `https://dashboard-provider.127.0.0.1.nip.io` | FDSC 管理界面 |
| Verifier | `https://verifier.mp-operations.org` | VCVerifier (凭证验证) |
| APISIX | `https://mp-data-service.127.0.0.1.nip.io` | API Gateway |

## API 端点 (Mock Provider)

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/` | GET | API 根目录 | ❌ |
| `/health` | GET | 健康检查 | ❌ |
| `/api/catalog` | GET | 数据目录 | ❌ |
| `/api/catalog/{id}` | GET | Offering 详情 (含 metadata + contract) | ❌ |
| `/api/catalog/offerings` | POST | 发布 Offering | ✅ |
| `/api/contract-negotiations` | POST | 发起协商 | ✅ |
| `/api/transfer-processes` | POST | 发起传输 | ✅ |
| `/api/energy/buildings/hourly` | GET | 建筑能耗数据 | ✅ |
| `/api/metadata` | GET | 元数据 (JSON-LD) | ❌ |
| `/auth/token` | POST | 获取 JWT Token | ❌ |

## 数据格式

### 能耗数据

```json
{
  "datasetId": "building-energy-hourly-v1",
  "providerName": "Energy Data Provider Ltd.",
  "license": "CC-BY-4.0",
  "records": [
    {
      "buildingId": "BLD-001",
      "meterId": "MTR-001",
      "timestamp": "2026-05-01T00:00:00+08:00",
      "energyKWh": 12.4,
      "unit": "kWh",
      "location": {"city": "Shenzhen", "district": "Nanshan"}
    }
  ]
}
```

### 元数据 (JSON-LD)

```json
{
  "@context": {"dcat": "http://www.w3.org/ns/dcat#", "dct": "http://purl.org/dc/terms/"},
  "@type": "dcat:Dataset",
  "dct:title": "Building Energy Consumption Dataset API",
  "ex:datasetId": "building-energy-hourly-v1",
  "ex:unit": "kWh"
}
```

## 与 FIWARE DSC 的对应关系

| 演示组件 | FIWARE DSC 组件 | 说明 |
|---------|----------------|------|
| `/auth/token` | VCVerifier + Keycloak | 身份认证和令牌签发 |
| TMForum API | Product Catalog Manager | 数据目录、Offering 管理 |
| Scorpio | Context Broker | NGSI-LD 数据存储与查询 |
| Contract Negotiation | EDC Connector | 合同协商状态机 |
| Transfer Process | EDC Connector | 数据传输状态机 |
| TIR/TIL | Trusted Issuers Registry | DID 注册与验证 |

## 停止与重启集群

### 停止集群（关机前）

```bash
just down                    # 一键停止: clean + k3s-stop
```

或者手动分步执行：

```bash
just clean                   # 卸载 Helm releases + 删除命名空间
docker stop k3s-server && docker rm k3s-server   # 停止 k3s 容器
```

`just clean` 只删除 Helm releases 和命名空间，**不会删除 Docker 卷 `k3s-data`**。k3s 内部的容器镜像缓存保留在该卷中，下次启动时不需要重新拉取。

### 重启集群

```bash
just k3s-start               # 启动 k3s 容器（使用已有的 k3s-data 卷）
export KUBECONFIG=/tmp/k3s.yaml
just deploy-all              # 部署 trust-anchor + provider + consumer
```

整个重启过程约 3-5 分钟，无需重新下载镜像。

## 参考部署时长

在 8 核 CPU / 32 GB 内存 / SSD 的本地环境下，首次完整部署大致耗时如下：

| 阶段 | 命令 | 参考时长 | 说明 |
|------|------|---------|------|
| 启动 k3s 容器 | `just k3s-start && just k3s-wait` | 1-2 分钟 | 依赖 Docker 镜像是否已缓存 |
| 部署基础设施 | `just deploy-infra` | 2-3 分钟 | cert-manager + Zalando postgres-operator |
| 创建 CA issuer | 手动 apply | < 1 分钟 | 一次创建，后续复用 |
| 部署 Trust Anchor | `just deploy-trust-anchor` | 2-3 分钟 | 使用 H2 内存数据库 |
| 部署 Provider | `helm install provider ...` | 8-15 分钟 | 主要耗时在镜像拉取与 BAE 启动 |
| Provider 手动补丁 | 见部署笔记 4.12-4.14 | 5-10 分钟 | MongoDB SA、agent 镜像、用户与认证机制 |
| 部署 Consumer | `helm install consumer ...` | 3-5 分钟 | 需禁用嵌套 postgres-operator |
| Consumer 手动补丁 | 见部署笔记 4.8、4.15 | < 5 分钟 | 创建 keystore-password Secret |
| 配置 Ingress | `helm install ingress-nginx ...` + patch | 1-2 分钟 | 设置 ingressClassName |
| **首次部署总计** | — | **约 15-25 分钟** | 不含镜像下载等待时间 |
| 健康检查 | `just demo-cluster-health` | 10-30 秒 | 7 个 ingress 端点 |
| Real Cluster Demo | `just demo-cluster` | 1-2 分钟 | 完整数据交换流程 |

> **注意：** 若 Docker Hub 或 quay.io 网络不稳定，镜像拉取可能额外耗时 5-20 分钟。建议首次部署前检查网络，或预先拉取关键镜像。

### 完全清理（释放磁盘空间）

```bash
just clean
docker stop k3s-server && docker rm k3s-server
docker volume rm k3s-data    # 删除卷后需要重新拉取镜像
```

## 故障排除

### 端口被占用

```bash
lsof -i :8000
kill -9 <PID>
```

### 依赖问题

```bash
cd demo && uv sync --reinstall
```

### k3s 集群问题

```bash
just k3s-status              # 检查 k3s 容器
just pods                    # 查看所有 Pod
just events                  # 查看事件
just logs-keycloak           # 查看 Keycloak 日志
just releases                # 查看 Helm releases
```

### Ingress 不通

```bash
# 检查 nginx-ingress controller
kubectl get pods -n ingress-nginx

# 检查 ingress class
kubectl get ingressclass

# 检查 ingress 资源
kubectl get ingress -A
```

### 常见部署错误速查

| 错误现象 | 最可能原因 | 快速修复 |
|---------|-----------|---------|
| Certificate 一直处于 `Issuing` / `False` | `ca-secret` 或 `ca-issuer` 缺失 | 按部署笔记 4.11 创建自签名 CA 证书链 |
| Provider Keycloak `prepare-keystore` 失败 | `keystore-password` Secret 缺失 | `kubectl create secret generic keystore-password --from-literal=password=changeit -n provider` |
| Consumer Keycloak `prepare-keystore` 失败 | `keystore-password` Secret 缺失 | `kubectl create secret generic keystore-password --from-literal=password=changeit -n consumer` |
| `mongodb-0` 一直 `Pending` | `mongodb-database` ServiceAccount 缺失 | `kubectl create serviceaccount mongodb-database -n provider` |
| `mongodb-0` 的 `mongodb-agent` `ImagePullBackOff` | 镜像 tag 不存在 | 替换为本地已有镜像，如 `quay.io/mongodb/mongodb-agent-ubi:108.0.6.8796-1` |
| BAE charging / logic proxy `CrashLoopBackOff` | SCRAM-SHA-1/256 不匹配或 `charging`/`belp` 用户缺失 | 创建 SCRAM-SHA-256 用户并设置 `BAE_CB_MONGO_AUTH_MECHANISM=SCRAM-SHA-256` / `BAE_LP_MONGO_AUTH_MECHANISM=SCRAM-SHA-256` |
| Consumer Helm 安装失败，ClusterRole 冲突 | 嵌套 postgres-operator 与全局 operator 冲突 | 加 `--set decentralizedIam.vcAuthentication.postgres-operator.enabled=false` |
| 所有 Ingress 返回 404 | `ingressClassName` 未设置 | `kubectl get ingress -A -o name | xargs -I {} kubectl patch {} --type merge -p '{"spec":{"ingressClassName":"nginx"}}'` |
| `just smoke-test` 显示异常 Pod | 可能只是 mongodb-agent 镜像未就绪 | 查看 `kubectl describe pod mongodb-0 -n provider`，确认 mongod 容器是否 Running |

更详细的根因与完整修复命令见 [部署笔记 (A_fiware_deployment_notes.md)](./A_fiware_deployment_notes.md)。

## 相关文档

- [架构与通信流程](./ARCHITECTURE.md)
- [部署笔记 (踩坑记录 + 技术选型)](./A_fiware_deployment_notes.md)
- [数据交换 Demo (流程 + 踩坑 + 扩展指南)](./data_exchange_demo.md)
- [项目概述](../wiki/1-xiang-mu-gai-shu.md)
- [快速部署指南](../wiki/2-kuai-su-bu-shu-zhi-nan.md)
- [默认场景说明](./data/scenarios/DSSC_Minimal_Energy_Scenario/README.md)
- [默认场景验证指南](./data/scenarios/DSSC_Minimal_Energy_Scenario/VALIDATION_GUIDE.md)
- [集群排查记录](../doc/troubleshooting-k3s-deployment.md)
