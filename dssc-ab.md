# DSSC A/B 组对接说明

## 1. 文档目的

本文以 **FIWARE Real Cluster** 为 A 组正式交付基线，说明 A 组当前可向 B 组交付的数据、尚待交付或共同商议的数据，以及 FIWARE Connector/Catalogue 与 Gaia-X Compliance 两套架构之间的对象和标识差异。

`demo/` 中的 Mock Demo 只用于流程展示。Mock 生成的 Offering ID、Mock DID、localhost endpoint 和内存状态不作为正式交付值。

当前状态依据：

- Real Cluster 实现：`demo/demo_real_cluster.py`
- 最近一次完整运行记录：`demo/logs/demo-real-20260704-203904.log`
- 场景数据：`demo/data/scenarios/DSSC_Minimal_Energy_Scenario/`

## 2. 对接对象与统一术语

为避免 A、B 两组把不同对象都称为 “Offering”，双方采用以下术语：

| 术语 | 含义 | 当前标识 |
|---|---|---|
| Provider Participant | 在 Real Cluster 中提供数据服务的参与者 | `did:web:mp-operations.org` |
| Canonical Service Offering | 跨部署稳定的业务服务标识，供 Gaia-X Credential 描述 | 建议 `urn:dssc:service-offering:building-energy-hourly-v1` |
| ProductOffering Instance | TMForum Catalogue 中的一次实际发布记录 | `urn:ngsi-ld:product-offering:<runtime UUID>` |
| ProductSpecification Instance | TMForum Catalogue 中被 ProductOffering 引用的规格记录 | `urn:ngsi-ld:product-specification:<runtime UUID>` |
| Dataset | 跨系统关联的建筑能耗数据集 | `building-energy-hourly-v1` |
| Data Resource | Scorpio 中可访问的具体 NGSI-LD 资源 | `urn:ngsi-ld:Building:BLD-001` |

这些对象不能共用一个 ID。Canonical Service Offering 是稳定业务对象；ProductOffering Instance 和 ProductSpecification Instance 是具体部署产生的运行实例；Dataset 是数据产品；Data Resource 是数据集中的具体资源。

## 3. 当前可交付数据

### 3.1 Provider 身份

| 字段 | 可交付值 | 证据与说明 |
|---|---|---|
| Provider name | `Energy Data Provider Ltd.` | 场景配置、metadata 和样例数据一致 |
| Participant ID / DID | `did:web:mp-operations.org` | Real Cluster 已从 TIR 查询到该 DID |
| Role | `Data Provider` | A 组流程中创建并发布 ProductOffering、提供 Scorpio 数据 |
| TIR verification | 已注册 | 最近一次集群日志中 TIR 返回成功并包含该 DID |

`did:web:energy-provider.example.org` 和 `did:web:example.org` 是旧场景模板占位值，不作为 Real Cluster 的正式 Provider ID。

### 3.2 Product Offering 和数据资源

以下是最近一次成功运行产生的实例值：

| 字段 | 可交付值 | 性质 |
|---|---|---|
| ProductOffering ID | `urn:ngsi-ld:product-offering:9bf7b573-12c9-4e5c-8761-6df190965aa7` | 运行实例，每次重新发布可能变化 |
| ProductSpecification ID | `urn:ngsi-ld:product-specification:76ab9aad-8dc2-43c2-a6db-7191494a96eb` | 运行实例，每次重新发布可能变化 |
| Offering name | `Building Energy Consumption Data` | TMForum ProductOffering 实际名称 |
| Offering description | `Hourly energy consumption data for buildings in Shenzhen` | TMForum ProductOffering 实际描述 |
| Offering status | `Active` | TMForum `lifecycleStatus` |
| Dataset ID | `building-energy-hourly-v1` | 稳定业务关联键 |
| Data Resource ID | `urn:ngsi-ld:Building:BLD-001` | Scorpio NGSI-LD Entity ID |

Catalogue 查询入口：

```text
GET https://tm-forum-api.127.0.0.1.nip.io/tmf-api/productCatalogManagement/v4/productOffering
```

最近一次运行已完成 ProductSpecification 创建、ProductOffering 创建和 Consumer Catalogue 查询，可用运行日志作为 `connector-publication-result` 的等效证据。

### 3.3 API 与访问方式

Real Cluster 当前实际数据访问方式为：

```text
GET https://scorpio-provider.127.0.0.1.nip.io/ngsi-ld/v1/entities/urn:ngsi-ld:Building:BLD-001
Accept: application/ld+json
```

| 字段 | 当前值 |
|---|---|
| Access type | API / NGSI-LD Entity API |
| HTTP method | `GET` |
| Resource format | NGSI-LD / JSON-LD |
| Response media type | `application/ld+json` |
| Deployment scope | 本地 Real Cluster |
| Publicly reachable | 否；通过本机 `nip.io` ingress 访问 |
| Authentication | Real Cluster 使用 Keycloak OIDC；当前 Scorpio 演示读取链路没有把合同结果作为访问令牌执行 |

现有场景 `openapi.yaml` 可以交付，但它描述的是目标业务接口：

```text
GET https://api.example.org/energy/buildings/hourly
application/json
```

它不是 Scorpio 实际接口的部署合同。A 组已新增 `demo/deliverables/openapi-scorpio.yaml`，专门描述 Real Cluster 当前实际调用，因此部署 endpoint 现在已有相符的接口说明；场景 OpenAPI 与部署 OpenAPI 仍应分开使用。

### 3.4 License、协商和传输记录

| 数据 | 当前值 | 证据等级 |
|---|---|---|
| License | CC-BY-4.0 | 场景数据和 metadata 已声明 |
| License URL | `https://creativecommons.org/licenses/by/4.0/` | 场景 metadata 已声明 |
| Negotiation ID | `neg-3a76d26a5871` | 最近一次运行记录 |
| Contract ID | `contract-b10af69c` | 最近一次运行记录 |
| Negotiation result | `AGREED` | Python 本地状态机模拟，不是 Connector API 返回 |
| Transfer ID | `transfer-f5c6af38d62c` | 最近一次运行记录 |
| Transfer result | `COMPLETED` | Python 本地状态机模拟，不是 Connector API 返回 |

TMForum 发布、Catalogue 查询、TIR 查询、Keycloak 认证以及 Scorpio 写入/读取是真实集群调用。Contract Negotiation 和 Transfer Process 目前是 `demo_real_cluster.py` 中的本地状态机，应以 `executionMode: simulated-state-machine` 交付，不能表述为 Connector 实际执行结果。

## 4. 待交付数据

### 4.1 已完成的 A 组补齐工作

| 已完成项 | 结果 |
|---|---|
| `provider-profile.json` | 已生成 Provider DID、角色、TIR 来源和合规状态说明 |
| `offering-manifest.json` | 已区分 Canonical Offering、TMForum 实例、Dataset 与 Scorpio Resource |
| `connector-publication-result.json` | 已将最近一次真实集群日志转为结构化快照；后续完整运行会自动刷新 |
| `contract-transfer-result.json` | 已结构化保存状态历史，并明确 `connectorExecuted: false` |
| Offering version | ProductSpecification、ProductOffering 和 manifest 统一使用 `0.1.0` |
| Real Cluster policy 表达 | 新发布请求已加入 ODRL access/contract policy、署名义务和禁止再分发规则；license 与 purpose 保留在 manifest 中 |
| 与实际 endpoint 对应的接口描述 | 已新增 `openapi-scorpio.yaml` 描述实际 NGSI-LD Entity API |
| 自动导出 | `demo_real_cluster.py full` 完成后自动刷新四个 JSON 交付文件，不写入 token、密码或私钥；文件包含版本、生成时间和责任组 |

其中 ODRL policy、新增 Offering 字段和能耗 readings 已经完成代码实现，但尚未在本轮重新运行 Real Cluster 发布验证；当前结构化快照明确区分 2026-07-04 的 `observedAt` 与事后整理文件的 `generatedAt`，Canonical Offering 映射标记为提案而不是历史观察事实。

### 4.2 仍待 A 组处理的数据

以下内容仍需要 A 组后续实现或确定：

| 待交付项 | 原因 |
|---|---|
| Provider 公开主页或标识 URL | 当前没有受项目控制、可长期访问的 URL |
| Dataset URI | 有稳定 Dataset ID，但尚未共同确定用于 `gx:aggregationOf` 的最终 URI/IRI |
| 数据保留要求 | 场景和 Real Cluster 均未定义 |
| Connector 执行的合同规则 | 当前 negotiation/transfer 是本地模拟，尚无真实 Connector 协议证据 |
| ODRL policy 集群验证 | 新请求结构已实现，仍需下一次 Real Cluster 完整运行确认 TMForum 接收并原样返回 |

## 5. 待 A/B 两组商议的数据

### 5.1 Provider DID 的语义角色

建议在本次演示范围内采用：

```text
LegalPerson.credentialSubject.id = did:web:mp-operations.org
ServiceOffering.gx:providedBy    = did:web:mp-operations.org
```

B 组仍需确认：

- 是否接受它作为 Gaia-X Legal Participant subject；
- LegalPerson 和 ServiceOffering Credential 分别由谁签发；
- 该 DID 的 DID Document、verification method 和证书链是否满足 B 组的 Gaia-X 验证要求。

原因：FIWARE TIR 注册只能证明该 DID 在当前 FIWARE 环境中的技术信任状态，不能自动证明法律注册、Gaia-X Trust Anchor 或 Compliance 状态。Credential 的 `issuer` 也不应与被描述的 `credentialSubject.id` 混为一谈。

### 5.2 稳定 Service Offering URI

建议使用：

```text
urn:dssc:service-offering:building-energy-hourly-v1
```

并令：

```text
ServiceOffering.credentialSubject.id = Canonical Service Offering ID
```

B 组需要确认其 Gaia-X shape 和验证工具是否接受 URN 形式的 IRI。如果必须使用 HTTPS URI，双方应选择受控域名，不能继续使用 `example.org` 占位地址。

不建议把 TMForum 的 UUID 直接写成 ServiceOffering Credential subject，因为重新发布或重建集群会产生新 UUID，导致 Credential 与稳定业务服务解绑。

### 5.3 正式 endpoint

当前唯一有运行证据的 endpoint 是本地 Scorpio NGSI-LD API，因此它应作为本轮 Real Cluster 部署 endpoint。双方仍需选择最终交付策略：

1. 接受 Scorpio NGSI-LD endpoint，并使用已补充的 `openapi-scorpio.yaml`；或
2. 由 A 组通过 APISIX/适配服务部署 `/energy/buildings/hourly`，使 Real Cluster 与现有 OpenAPI 一致。

在第二项完成前，B 组 Credential 不应把 `https://api.example.org/energy/buildings/hourly` 描述成已经部署的正式 endpoint。

### 5.4 稳定语义 ID 与运行实例 ID 的映射

建议双方正式接受以下关系：

```text
Canonical Service Offering  1 ── 0..N Deployment Instances
Deployment Instance         1 ── 1 TMForum ProductOffering
TMForum ProductOffering     1 ── 1 ProductSpecification
Canonical Service Offering  1 ── 1 Dataset
Dataset                     1 ── 1..N Data Resources
```

推荐 manifest 表达：

```json
{
  "canonicalOffering": {
    "id": "urn:dssc:service-offering:building-energy-hourly-v1",
    "providerId": "did:web:mp-operations.org",
    "datasetId": "building-energy-hourly-v1",
    "version": "0.1.0"
  },
  "deployment": {
    "platform": "FIWARE Data Space Connector",
    "environment": "local-real-cluster",
    "productOfferingId": "urn:ngsi-ld:product-offering:9bf7b573-12c9-4e5c-8761-6df190965aa7",
    "productSpecificationId": "urn:ngsi-ld:product-specification:76ab9aad-8dc2-43c2-a6db-7191494a96eb",
    "resourceIds": ["urn:ngsi-ld:Building:BLD-001"],
    "endpoint": "https://scorpio-provider.127.0.0.1.nip.io/ngsi-ld/v1/entities/urn:ngsi-ld:Building:BLD-001"
  }
}
```

该映射允许集群重建、重复发布和多环境部署，而不要求 B 组为每个运行 UUID 重新定义业务对象或重新签发稳定身份 Credential。

## 6. A/B 两组架构差异

| 维度 | A 组：FIWARE Real Cluster | B 组：Gaia-X Compliance / Registry | 对接含义 |
|---|---|---|---|
| 核心目标 | 发布、发现和访问数据服务 | 描述并验证参与者与服务的信任、合规声明 | B 组验证声明，不代替 A 组执行数据交换 |
| 主要对象 | TMForum ProductOffering、ProductSpecification、Scorpio Entity | LegalPerson Credential、ServiceOffering Credential、VP/VC | 对象不能仅凭名称直接一一等同 |
| Participant 身份 | DID 用于 FIWARE TIR、认证和参与者识别 | DID 同时参与 Credential subject、issuer、签名和信任链验证 | 必须区分 Provider subject 与 Credential issuer |
| Offering 身份 | Catalogue 创建运行实例并可能生成 UUID | Credential subject 应长期稳定、可重复引用 | 需要 canonical ID 到 deployment ID 的映射 |
| 生命周期 | 部署、发布、重建和重复运行 | 签发、验证、过期、撤销 | 运行实例变化不应迫使稳定 Credential 随之变化 |
| Endpoint | 环境相关的 Scorpio/APISIX/Ingress 地址 | ServiceOffering 对访问方式的声明 | Credential 声明必须对应真实部署，但不应把 endpoint 当成业务身份 |
| Policy | 应由 Connector/Catalogue/网关在访问时执行 | 以 `gx:policy`、条款和 Credential 表达 | B 组声明与 A 组执行必须语义一致，但结构可以不同 |
| Negotiation/Transfer | 应产生协议状态并实际控制访问 | 用于串联合规后的业务流程，不负责执行 | 当前 A 组为模拟状态，必须如实标注 |
| 验证证据 | API 响应、Catalogue 记录、集群日志、资源读取结果 | VC/VP、Compliance Credential、Registry/Trust Anchor 结果 | 最终演示应并列保存两类证据 |
| 部署边界 | 本地 k3s、`nip.io`、运行时资源 | 可面向公开 DID、证书和远程 Compliance 服务 | 本地 endpoint 可演示，但不等同于公开可验证身份基础设施 |

## 7. 推荐的跨组集成边界

A 组负责：

- 提供 Provider、Canonical Offering、Dataset 和部署实例之间的映射；
- 提供 TMForum 发布、Catalogue 查询、Keycloak 认证和 Scorpio 数据访问证据；
- 明确哪些步骤是真实组件调用，哪些仍是模拟；
- 使实际执行的 license/policy 与交付声明保持一致。

B 组负责：

- 根据双方确认的稳定身份生成或校对 LegalPerson、ServiceOffering Credential；
- 决定 Credential issuer、签名、DID 解析和 Gaia-X Trust Anchor；
- 验证 `gx:providedBy`、`gx:aggregationOf`、条款和 policy 的合规表达；
- 接受 deployment mapping，避免把运行 UUID 当作唯一稳定业务身份。

双方共同负责：

- 确认 Provider DID 在 Gaia-X 模型中的角色；
- 确认 Canonical Service Offering ID 的 URI 形式；
- 选择最终 endpoint 策略；
- 确认 Dataset URI；
- 对齐 A 组实际执行 policy 与 B 组 Credential 声明；
- 在演示输出中区分稳定业务标识、部署实例标识和一次运行产生的流程 ID。

## 8. 当前建议结论

1. Real Cluster 是唯一正式交付基线，Mock Demo 不参与正式 ID 对齐。
2. `did:web:mp-operations.org` 暂定为 Provider Participant ID，Gaia-X 法律和签发角色由 B 组验证。
3. 使用稳定 Canonical Service Offering ID，不把 TMForum 运行 UUID直接作为 Gaia-X Credential subject。
4. 当前正式部署 endpoint 是 Scorpio NGSI-LD 本地地址，并由 `openapi-scorpio.yaml` 描述；原场景 OpenAPI 继续作为未来业务适配接口的目标合同。
5. A、B 两组应接受“稳定语义对象—运行部署实例”的显式映射，并分别保留 Compliance 证据与 Data Exchange 证据。
