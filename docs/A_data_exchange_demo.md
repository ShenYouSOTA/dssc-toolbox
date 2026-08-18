# 数据交换 Demo 文档

本文档详细说明 Mock Demo 和 Real Cluster Demo 的数据交换流程、开发踩坑记录和技术选型分析。

---

## 1. 概述

### 1.1 与 ARCHITECTURE.md 和 README 的关系

| 文档 | 侧重点 | 适合阅读场景 |
|------|--------|-------------|
| **README.md** | 使用说明、命令速查 | 快速上手 |
| **ARCHITECTURE.md** | 通信流程图、时序图、代码位置 | 理解架构 |
| **本文档** | 踩坑记录、技术选型、扩展指南 | 开发调试、二次开发 |

### 1.2 两种 Demo 的适用场景

| 场景 | 推荐 Demo | 理由 |
|------|-----------|------|
| 学习数据空间概念 | Mock | 无环境依赖，流程清晰 |
| 开发新功能 | Mock | 快速迭代，无需等集群部署 |
| 验证集群部署 | Real Cluster | 真实组件，端到端验证 |
| 集成测试 | Real Cluster | 真实网络、认证、存储 |
| 演示/Presentation | Mock | 确定性输出，不受集群状态影响 |

---

## 2. 数据交换核心流程

### 2.1 Mock Demo 流程

```
Provider (FastAPI :8000)                Consumer (DSSCConsumer)
    │                                        │
    │  ① POST /auth/token                    │
    │  {client_id, client_secret}            │
    │◄───────────────────────────────────────│
    │  → 验证凭证 → 签发 JWT                 │
    │  ──→ access_token                      │
    │                                        │
    │  ② POST /api/catalog/offerings         │
    │  Authorization: Bearer xxx             │
    │◄───────────────────────────────────────│
    │  → 加载 metadata/data-product-valid.jsonld
    │  → 加载 mock-api/openapi.yaml          │
    │  → 组装 DataOffering 存入内存          │
    │  ──→ offering (含 metadata + contract) │
    │                                        │
    │  ③ GET /api/catalog                    │
    │◄───────────────────────────────────────│
    │  ──→ catalog list                      │
    │                                        │
    │  ④ GET /api/catalog/{id}               │
    │◄───────────────────────────────────────│
    │  ──→ offering detail (metadata+contract)│
    │                                        │
    │  ⑤ POST /api/contract-negotiations     │
    │  {offeringId, consumerDID}             │
    │◄───────────────────────────────────────│
    │  → 内存状态机: REQUESTED→CONFIRMED→AGREED│
    │  → 生成 contractId                     │
    │  ──→ negotiation {state: AGREED}       │
    │                                        │
    │  ⑥ POST /api/transfer-processes        │
    │  {negotiationId}                       │
    │◄───────────────────────────────────────│
    │  → 检查 negotiation.state == AGREED    │
    │  → 内存状态机: REQUESTED→STARTED→COMPLETED│
    │  → 生成 resourceAddress                │
    │  ──→ transfer {state: COMPLETED}       │
    │                                        │
    │  ⑦ GET /api/energy/buildings/hourly    │
    │  Authorization: Bearer xxx             │
    │  ?buildingId=BLD-001                   │
    │◄───────────────────────────────────────│
    │  → 验证 JWT                            │
    │  → 加载 data/building-energy-sample.json│
    │  → 按参数过滤                          │
    │  ──→ EnergyDataset {records: [...]}    │
```

**代码位置：**
- `provider_server.py:288-315` — 认证端点，签发 JWT
- `provider_server.py:337-395` — Offering 创建，加载 JSON-LD + OpenAPI
- `provider_server.py:446-492` — 协商状态机，自动流转到 AGREED
- `provider_server.py:521-578` — 传输状态机，检查前置条件后自动流转
- `provider_server.py:603-640` — 数据端点，验证 token 后返回过滤数据
- `consumer_client.py:55-84` — 目录发现
- `consumer_client.py:124-165` — 认证
- `consumer_client.py:166-210` — 协商
- `consumer_client.py:262-313` — 数据获取

### 2.2 Real Cluster Demo 流程

```
Python Client               k3s 集群 (via nginx-ingress)
    │                              │
    │  ① 健康检查 (7 个端点)       │
    │  GET /v4/issuers (TIR)       │
    │  GET /realms/test-realm (KC) │
    │  GET /tmf-api/.../catalog    │
    │  GET /issuer (TIL)           │
    │  GET / (Dashboard)           │
    │  GET /ngsi-ld/v1/entities    │
    │─────────────────────────────→│  并行检查 7 个服务
    │  ◄── 各服务状态 ────────────│
    │                              │
    │  ② 创建 Data Offering        │
    │  POST /ngsi-ld/v1/entities   │
    │  Host: scorpio-provider      │
    │─────────────────────────────→│  Scorpio: 创建 Building 实体
    │  ◄── 201 Created ───────────│  (或 409 已存在)
    │                              │
    │  POST /tmf-api/.../productSpec│
    │  Host: tm-forum-api          │
    │─────────────────────────────→│  TMForum: 创建 ProductSpecification
    │  ◄── spec_id ───────────────│
    │                              │
    │  POST /tmf-api/.../productOffering│
    │  Host: tm-forum-api          │
    │─────────────────────────────→│  TMForum: 创建 ProductOffering
    │  ◄── offering_id ───────────│  (productOfferingTerm 携带 ODRL
    │                              │   accessPolicy + contractPolicy,
    │                              │   含 P30D 数据保留 duty)
    │  ②.5 ODRL Policy 回读校验    │
    │  GET /tmf-api/.../productOffering/{id}│
    │─────────────────────────────→│  TMForum: 读回 Offering
    │  ◄── offering ──────────────│  比对 access/contract policy
    │                              │  是否原样保留（归一化后比较）
    │                              │
    │  ③ Consumer 发现 Catalog     │
    │  GET /tmf-api/.../productOffering│
    │─────────────────────────────→│  TMForum: 查询所有 Offerings
    │  ◄── offerings list ────────│
    │                              │
    │  ④ Consumer 认证             │
    │  GET /realms/test-realm      │
    │─────────────────────────────→│  Consumer Keycloak: 获取 realm info
    │  ◄── token_endpoint ────────│
    │                              │
    │  POST {token_endpoint}       │
    │  grant_type=password         │
    │  username=employee&password=test│
    │─────────────────────────────→│  Consumer Keycloak: OIDC token
    │  ◄── access_token ──────────│
    │                              │
    │  ⑤ Contract Negotiation      │
    │  (本地 dataclass 模拟)        │
    │  REQUESTED → CONFIRMED → AGREED│
    │  生成 negotiation_id, contract_id│
    │                              │
    │  ⑥ Transfer Process          │
    │  (本地 dataclass 模拟)        │
    │  REQUESTED → STARTED → COMPLETED│
    │  生成 transfer_id            │
    │                              │
    │  ⑦ 获取数据                  │
    │  GET /ngsi-ld/v1/entities/urn:ngsi-ld:Building:BLD-001│
    │  Host: scorpio-provider      │
    │─────────────────────────────→│  Scorpio: 读取实体
    │  ◄── entity JSON-LD ────────│
```

**代码位置：**
- `demo_real_cluster.py:250-280` — 健康检查（7 个端点并行）
- `demo_real_cluster.py:341-527` — 创建 Offering（Scorpio + TMForum + Policy 回读 + TIR 验证）
- `demo_real_cluster.py:282-340` — ODRL policy 回读校验（含单元素数组归一化）
- `demo_real_cluster.py:528-554` — Catalog 发现
- `demo_real_cluster.py:555-613` — Keycloak 认证
- `demo_real_cluster.py:614-666` — Contract Negotiation（本地 dataclass）
- `demo_real_cluster.py:667-713` — Transfer Process（本地 dataclass）
- `demo_real_cluster.py:714-745` — 数据获取

---

## 3. 踩坑记录

### 3.1 Mock Demo 开发踩坑

#### 3.1.1 FastAPI 启动方式选择

**问题：** 需要在 demo 中同时运行 FastAPI 服务器和 Consumer 客户端。

**方案对比：**

| 方案 | 优点 | 缺点 |
|------|------|------|
| `uvicorn.run()` 直接启动 | 简单直接 | 阻塞主线程 |
| `threading.Thread` 后台线程 | 可在同一进程内运行客户端 | 需要等待服务器就绪 |
| `multiprocessing` | 完全隔离 | 增加复杂度，端口冲突风险 |

**选择：** `threading.Thread` + daemon=True，配合 `wait_for_server()` 轮询。

```python
# run_demo.py:132-138
server_thread = threading.Thread(
    target=uvicorn.run,
    args=(app,),
    kwargs={"host": MOCK_HOST, "port": MOCK_PORT, "log_level": "warning"},
    daemon=True,
)
server_thread.start()
```

#### 3.1.2 JWT 验证中间件设计

**问题：** 需要保护数据端点（`/api/energy/*`），但公开端点（`/api/catalog`）不需要认证。

**解决方案：** 在每个需要认证的端点函数内部手动调用 `verify_token()`，而非使用 FastAPI 的 `Depends` 中间件（因为部分端点可选认证）。

```python
# provider_server.py:317-327
def verify_token(authorization: str) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return payload
```

#### 3.1.3 状态机自动流转 vs 手动确认

**问题：** Contract Negotiation 和 Transfer Process 应该自动流转还是等待手动确认？

**Trade-off：**
- 自动流转：Demo 流程顺畅，但不符合真实场景
- 手动确认：更真实，但增加 Demo 复杂度

**选择：** 自动流转（Demo 优先考虑演示效果），但在状态历史中记录每一步。

```python
# provider_server.py:446-492
# 创建 negotiation 后立即自动推进到 AGREED
neg.state = NegotiationState.REQUESTED
neg.state_history.append(...)
neg.state = NegotiationState.CONFIRMED
neg.state_history.append(...)
neg.state = NegotiationState.AGREED
neg.state_history.append(...)
```

#### 3.1.4 文件路径处理

**问题：** Demo 运行时的当前目录不确定，且数据硬编码在仓库根目录的 `DSSC_Tool_Learning/` 下，导致 `demo/` 无法自包含，也不方便替换为真实数据。

**解决方案：** 把数据复制到 `demo/data/scenarios/<scenario-name>/`，用 `Path(__file__).parent` 建立相对于 `demo/` 的路径，并通过环境变量切换 scenario 和具体文件。

```python
# config.py:15-65
DEMO_DIR = Path(__file__).parent
SCENARIOS_DIR = DEMO_DIR / "data" / "scenarios"
DEFAULT_SCENARIO = os.environ.get("DEMO_SCENARIO", "DSSC_Minimal_Energy_Scenario")


def scenario_dir(name: str | None = None) -> Path:
    return SCENARIOS_DIR / (name or DEFAULT_SCENARIO)


def scenario_data_dir(name: str | None = None) -> Path:
    return scenario_dir(name) / "data"


def scenario_metadata_dir(name: str | None = None) -> Path:
    return scenario_dir(name) / "metadata"


def scenario_mock_api_dir(name: str | None = None) -> Path:
    return scenario_dir(name) / "mock-api"


# 默认 scenario 的兼容别名
DATA_DIR = scenario_data_dir()
METADATA_DIR = scenario_metadata_dir()
OPENAPI_DIR = scenario_mock_api_dir()
```

新增 scenario 时，只需在 `demo/data/scenarios/` 下创建同名目录并放入 `data/`、`metadata/`、`mock-api/` 等文件，然后通过 `DEMO_SCENARIO=<name>` 切换。

### 3.2 Real Cluster Demo 开发踩坑

#### 3.2.1 Keycloak Token Endpoint 格式差异

**现象：** Consumer Keycloak 的 realm 响应中没有 `token_endpoint` 字段，只有 `token-service` 字段。

**根因：** Consumer Keycloak 使用的版本返回 legacy 格式，`token-service` 需要拼接 `/token` 才能得到完整端点。

**解决方案：** 优先使用 `token_endpoint`，回退到 `token-service` + `/token`，最后使用默认路径。

```python
# demo_real_cluster.py:567-576
realm = resp.json()
token_endpoint = realm.get("token_endpoint", "")
if not token_endpoint:
    token_service = realm.get("token-service", "")
    if token_service:
        token_endpoint = f"{token_service}/token"
if not token_endpoint:
    token_endpoint = f"{ENDPOINTS['Consumer Keycloak']}/realms/{KC_REALM}/protocol/openid-connect/token"
```

#### 3.2.2 Scorpio 健康检查返回 400

**现象：** `GET /ngsi-ld/v1/entities` 返回 400 而非 200。

**根因：** Scorpio 对空查询（无参数）返回 400 Bad Request，这是 NGSI-LD 规范的行为，不是服务故障。

**解决方案：** 健康检查时将期望状态码设为 400。

```python
# demo_real_cluster.py:269
results["Scorpio"] = check_endpoint(client, "Scorpio",
    f"{ENDPOINTS['Scorpio']}/ngsi-ld/v1/entities", expect_status=400)
```

#### 3.2.3 TMForum API 不幂等

**现象：** 每次运行 Demo，TMForum API 中的 Offerings 数量不断累积。

**根因：** TMForum API 的 `POST /productOffering` 每次都会创建新记录，不检查是否已存在相同名称的 Offering。

**解决方案：** 当前 Demo 接受累积行为（不清理旧数据）。如需幂等，可先查询再创建或使用 `PUT` 更新。

#### 3.2.4 Contract Management API 404

**现象：** `GET /contract-management.127.0.0.1.nip.io/` 返回 404。

**根因：** Contract Management 服务不暴露标准的 REST API。它通过 TMForum API 的通知机制工作（`notification.enabled: true`），提供的是内部服务间通信，而非面向外部的 API。

**解决方案：** 使用本地 `dataclass` 模拟 Negotiation 和 Transfer 状态流转。

```python
# demo_real_cluster.py:190-217
@dataclass
class NegotiationState:
    negotiation_id: str = ""
    state: str = "INITIATED"
    state_history: list = field(default_factory=list)

@dataclass
class TransferState:
    transfer_id: str = ""
    state: str = "INITIATED"
    state_history: list = field(default_factory=list)
```

#### 3.2.5 nginx-ingress 配置

**现象：** 初始部署后所有 Ingress 返回 404。

**根因：** FDSC Chart 的 Ingress 资源使用 Traefik 注解，未设置 `spec.ingressClassName`。安装 nginx-ingress 后，需要明确指定 `ingressClassName: nginx`。

**解决方案：** 批量 patch 所有 Ingress。

```bash
kubectl get ingress -A -o name | xargs -I {} kubectl patch {} \
    --type merge -p '{"spec":{"ingressClassName":"nginx"}}'
```

#### 3.2.6 nip.io 域名解析

**现象：** 本地无法解析 `*.127.0.0.1.nip.io` 域名。

**根因：** nip.io 是公共 DNS 服务，需要网络通畅才能解析。

**解决方案：** 确保网络连接正常。如在离线环境，需在 `/etc/hosts` 中手动添加映射。

#### 3.2.7 productOfferingTerm 扩展字段必须声明 @schemaLocation

**现象：** `POST /productOffering` 返回 400，错误信息为 `If no schema is provided, no additional properties are allowed`，引用链指向 `productOfferingTerm[0]`。

**根因：** FIWARE TMForum API 对 ProductOfferingTerm 中的未知属性（`accessPolicy`/`contractPolicy`）要求显式声明 `@schemaLocation`，否则拒绝反序列化。官方 DSC 文档使用 EDC contract-definition schema。

**解决方案：** 在 term 中加入 schema 声明（参考 `data-space-connector/doc/DSP_INTEGRATION.md`）。

```python
# demo_real_cluster.py:440-442
{
    "name": "edc:contractDefinition",
    "@schemaLocation": "https://raw.githubusercontent.com/wistefan/edc-dsc/refs/heads/init/schemas/contract-definition.json",
    "accessPolicy": {...},
    "contractPolicy": {...},
}
```

#### 3.2.8 TMForum VO 不支持 externalId

**现象：** payload 中加入 `externalId`（或 `externalIdentifier`）后返回 400 `Schema validation failed with message If no schema is provided, no additional properties are allowed`。

**根因：** 当前部署的 FIWARE TMForum API 版本的 ProductOfferingCreateVO 未定义 `externalId`/`externalIdentifier` 字段；一旦请求中存在 `@schemaLocation`，整个 VO 会走严格 schema 校验，未知字段即被拒绝。

**解决方案：** 从 API payload 中移除该字段。规范 Offering ID（`urn:dssc:service-offering:building-energy-hourly-v1`）保留在交付件 `offering-manifest.json` 中，与 TMForum 内部 `offering_id` 分离维护。

#### 3.2.9 TMForum 回读时单元素数组被折叠为对象

**现象：** 创建时提交 `permission: [{...}]`，GET 读回后变成 `permission: {...}`（对象而非数组），导致直接做 JSON 相等比较时报"policy 不一致"。

**根因：** TMForum API 的 JSON 序列化会把单元素数组折叠成对象（`permission`、`prohibition` 均如此；`duty` 等多元素数组保留数组形式）。

**解决方案：** 比较前对两侧做归一化：把 `permission`/`prohibition`/`duty` 下的单对象统一包装回列表再比较。

```python
# demo_real_cluster.py:282-291 (_normalize_odrl) + verify_policy_roundtrip 中的 canon()
def wrap_lists(n):
    if isinstance(n, dict):
        return {k: ([wrap_lists(v)] if k in ("permission", "prohibition", "duty") and isinstance(v, dict)
                    else wrap_lists(v)) for k, v in n.items()}
    ...
```

#### 3.2.10 k3s 容器重启后 kubeconfig 失效

**现象：** `just up` 报 `container name "/k3s-server" is already in use`；或 `just k3s-wait` 一直卡住。

**根因：** k3s 容器停止后 `just up` 会尝试 `docker run` 同名容器；另外容器重启后 `/tmp/k3s.yaml` 中的 server 地址/证书可能失效。

**解决方案：** 直接启动已有容器并刷新 kubeconfig：

```bash
docker start k3s-server
docker exec k3s-server cat /etc/rancher/k3s/k3s.yaml > /tmp/k3s.yaml
kubectl --kubeconfig=/tmp/k3s.yaml get nodes   # 确认 Ready
```

重启后 `mongodb-0` 可能长时间显示 `1/2 Running`：mongod 容器本身已 Ready，未就绪的是 `mongodb-agent` sidecar（仅 Operator 管理用途），不影响 Demo 运行（另见部署笔记 4.13）。

#### 3.2.11 Gaia-X Compliance 要求 x5c 信任锚，裸 JWK 被 L3 拦截（跨组联调）

**现象：** B 组用本仓库固定 DID 签发的 VP-JWT 送测 Gaia-X Compliance Service，5 个用例在 L3（信任锚）被拦截，1 个在 L2（签名）被拦截，内容层错误用例（INV-01~04）全部被前置屏蔽，只有篡改签名用例（INV-07）按预期在 L2 被检出。

**根因：** Gaia-X Credential Format 要求 DID 文档的 verification method 携带 X.509 证书链（x5c/x5u）并声明 `alg`，锚定到 Gaia-X 认可 CA；早期 did.json 只有 `publicKeyJwk` 裸公钥（kty/crv/x/y），不满足信任锚要求。

**解决方案：** `just did-cert` 生成 demo CA + 叶子证书链（叶子绑定 provider 公钥、SAN 为 DID），`just did-export-x5c` 重新生成 did.json——JWK 增加 `alg: "ES256"` 和 `x5c` 链，密钥材料不变，已签发 VC/VP-JWT 无需重签。自签 CA 不在公开 trust store 中，锚定校验预计仍失败，属本轮接受的已知限制；demo 级信任证明 = 公网 did.json 解析 + ES256 本地验签（详见部署笔记 7.5）。

### 3.3 Python 客户端踩坑

#### 3.3.1 httpx vs requests

**选择 httpx 的理由：**
- 原生支持 HTTP/2
- 同步/异步双模式
- 更好的超时控制
- 类型注解完善

```python
# demo_real_cluster.py:219-222
def get_client() -> httpx.Client:
    return httpx.Client(verify=False, timeout=30.0, follow_redirects=True)
```

#### 3.3.2 SSL 证书验证

**现象：** 访问集群 Ingress 时 SSL 验证失败。

**根因：** 集群使用 cert-manager 自签证书，本地无 CA 信任链。

**解决方案：** Demo 中使用 `verify=False` 跳过验证（仅限开发环境）。

```python
client = httpx.Client(verify=False, timeout=30.0, follow_redirects=True)
```

#### 3.3.3 数据格式差异

**现象：** Scorpio 返回 NGSI-LD 格式（`{type: "Property", value: ...}`），TMForum 返回 REST JSON 格式。

**根因：** 两个服务使用不同的数据模型：
- Scorpio: NGSI-LD（W3C 标准，JSON-LD 结构）
- TMForum: TMForum Open API（REST 风格，扁平 JSON）

**解决方案：** Demo 中分别处理两种格式，在输出时统一展示。

```python
# Scorpio 实体格式
entity = {
    "id": "urn:ngsi-ld:Building:BLD-001",
    "type": "Building",
    "name": {"type": "Property", "value": "Shenzhen Nanshan Tower"},
}

# TMForum Offering 格式
offering = {
    "id": "12345",
    "name": "Building Energy Consumption Data",
    "lifecycleStatus": "Active",
}
```

---

## 4. 技术选型

### 4.1 FIWARE DSC 规范约束

以下流程和数据模型由 FIWARE DSC 规范定义，Demo 必须遵循：

| 规范 | 说明 | Demo 实现 |
|------|------|-----------|
| **OID4VP** | OpenID for Verifiable Presentations | Mock: 模拟 JWT；Real: Keycloak OIDC |
| **Verifiable Credentials** | W3C VC 数据模型 | Keycloak 签发 SD-JWT / JWT_VC |
| **NGSI-LD** | 情境感知数据模型 (ETSI) | Scorpio 存储/查询实体 |
| **TMForum Open API** | 产品目录管理 API | ProductSpecification / ProductOffering |
| **DID** | 去中心化标识符 (W3C) | `did:web` 注册到 TIR；跨组签名身份 did.json 发布到 GitHub Pages（含 alg/x5c，见部署笔记 7.5） |
| **ODRL** | 策略描述语言 (W3C) | APISIX + OPA 策略执行 |
| **EBSI TIR** | 可信发行者注册表 | Trust Anchor 提供 TIR API |

### 4.2 Demo 自选实现

以下选择是 Demo 为了简化或演示效果而做的决策：

| 决策点 | 选择 | 理由 | 替代方案 |
|--------|------|------|---------|
| **Demo 语言** | Python | 开发快、依赖轻 | Java (官方 SDK) |
| **Mock 服务器** | FastAPI | 自动生成 OpenAPI 文档 | Flask, Express |
| **HTTP 客户端** | httpx | 同步/异步、HTTP/2 | requests, aiohttp |
| **状态机存储** | 内存字典 / dataclass | 简单、无外部依赖 | Redis, SQLite |
| **配置管理** | config.py | 类型安全、IDE 补全 | .env, YAML |
| **认证模拟** | JWT (HS256) | 简单、可本地验证 | 真实 OID4VP 流程 |
| **Offering 创建** | 从文件加载 metadata | 确定性输出 | 动态生成 |
| **数据源** | 静态 JSON 文件 | 可预测、易验证 | 数据库查询 |

### 4.3 Real Cluster 自选实现

| 决策点 | 选择 | 理由 | 替代方案 |
|--------|------|------|---------|
| **服务访问** | nginx-ingress 直连 | 无需 port-forward | kubectl port-forward |
| **域名解析** | nip.io | 无需修改 /etc/hosts | CoreDNS 配置 |
| **Offering 创建** | TMForum API | 真实产品目录操作 | Dashboard UI |
| **数据读取** | Scorpio 直连 | 简单直接 | 通过 APISIX 网关 |
| **Negotiation/Transfer** | 本地 dataclass | Contract Management API 不可用 | 等待 API 完善 |
| **健康检查** | 7 端点并行 | 快速、覆盖全面 | 逐个检查 |
| **ODRL policy 校验** | 创建后回读比对 | 确认 TMForum 原样保存 policy | 信任写入结果 |
| **数据保留要求** | ODRL duty (delete + P30D) | 写进 contractPolicy，随 Offering 发布 | 仅在 metadata 中声明 |

---

## 5. 扩展指南

### 5.1 添加新的数据源

推荐做法：新增一个 scenario 目录，而不是改动默认 scenario。

1. 在 `demo/data/scenarios/` 下新建目录，例如 `my-real-data/`
2. 在该目录下创建 `data/`、`metadata/`、`mock-api/` 子目录，并放入对应文件
3. 通过环境变量切换 scenario：
   ```bash
   cd demo && DEMO_SCENARIO=my-real-data uv run python run_demo.py
   ```
4. 如需使用同一 scenario 下的不同数据文件，可设置 `DEMO_DATA_FILE=real-buildings.json`
5. 在 `provider_server.py` 中添加新的 API 端点（参考 `get_energy_data()` 实现）
6. 在 `consumer_client.py` 中添加对应的获取方法

旧的学习资料目录 `DSSC_Tool_Learning/DSSC_Minimal_Energy_Scenario/` 仍保留，作为场景定义和验证的参考源；运行时 Demo 使用 `demo/data/scenarios/` 下的副本。

### 5.2 接入真实的 Contract Management API

当 Contract Management API 可用时：

1. 在 `demo_real_cluster.py` 的 `ENDPOINTS` 中添加 Contract Management 端点
2. 将 `step_contract_negotiation()` 中的本地 dataclass 替换为真实 API 调用
3. 将 `step_transfer_process()` 中的本地 dataclass 替换为真实 API 调用
4. 处理 API 的认证（需要 VC token）

### 5.3 添加新的 Consumer 角色

1. 在 `config.py` 中添加新的客户端凭证
2. 在 `consumer.yaml` 中配置新的 Keycloak 用户和角色
3. 在 Demo 中添加新的 Consumer 流程

### 5.4 集成 Gaia-X 合规验证

1. 在 `provider.yaml` 中启用 Gaia-X 相关配置
2. 使用 `mvn clean deploy -Plocal,gaia-x` 部署
3. 在 Demo 中添加合规验证步骤

---

## 6. 附录

### 6.1 关键代码片段

**Offering 创建（Mock）：**
```python
# provider_server.py:337-395
def create_offering():
    metadata = load_metadata()  # 从当前 scenario 加载 JSON-LD
    contract = load_openapi_spec()  # 从当前 scenario 加载 OpenAPI
    offering = DataOffering(
        offeringId=f"offering-{uuid.uuid4().hex[:8]}",
        metadata=metadata,
        contractTemplate=contract,
        ...
    )
    offerings[offering.offeringId] = offering
```

**Offering 创建（Real Cluster）：**
```python
# demo_real_cluster.py:341-527 (step_create_offering)
# 1. Scorpio: 创建 NGSI-LD 实体
resp = client.post(f"{ENDPOINTS['Scorpio']}/ngsi-ld/v1/entities", json=entity)
# 2. TMForum: 创建 ProductSpecification
resp = client.post(f"{ENDPOINTS['TMForum API']}/tmf-api/.../productSpecification", json=spec)
# 3. TMForum: 创建 ProductOffering (引用 spec, term 携带 ODRL policy + @schemaLocation)
resp = client.post(f"{ENDPOINTS['TMForum API']}/tmf-api/.../productOffering", json=offering)
# 4. 回读校验: GET offering, 归一化后比对 access/contract policy
policy_verification = verify_policy_roundtrip(client, offering_id, offering)
```

**ODRL contractPolicy（含数据保留要求）：**
```python
# demo_real_cluster.py:44-47 + step_create_offering 中的 productOfferingTerm
RETENTION_PERIOD = "P30D"   # 合同达成后 30 天内必须删除数据
contractPolicy = {
    "permission": [{"action": "use", "duty": [
        {"action": "attribute"},
        {"action": "delete", "constraint": {
            "leftOperand": "odrl:elapsedTime", "operator": "gteq",
            "rightOperand": {"@value": "P30D", "@type": "xsd:duration"}}},
    ]}],
    "prohibition": [{"action": "distribute"}],
}
```

### 6.2 配置项速查表

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
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

### 6.3 相关文档

- [架构与通信流程](../demo/ARCHITECTURE.md)
- [部署笔记](./A_fiware_deployment_notes.md)
- [README](../demo/README.md)
- [项目概述](../wiki/1-xiang-mu-gai-shu.md)
- [OID4VC 认证框架](../wiki/9-oid4vc-ren-zheng-kuang-jia-vcverifier-trusted-issuers-list.md)
- [TMForum Open API 流程](../wiki/13-tm-forum-open-apis-he-tong-guan-li-liu-cheng.md)
