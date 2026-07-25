# FIWARE Data Space Connector 与 TNO Security Gateway 对比

## 1. 研究问题

本文围绕三个问题比较 FIWARE Data Space Connector（FIWARE DSC）与 TNO Security Gateway（TNO TSG）：

1. 哪一个更接近数据空间协议研究？
2. 两者的组件边界和技术重点有什么不同？
3. 哪一个更适合作为教学 Demo，以及如何用于 Building Energy Consumption Data Product 项目？

> **版本说明：**早期 TNO TSG 资料常使用 IDS Core Container、Data Apps、DAPS/DAT 等术语；当前 TSG 已发展为完整的 Participant Agent，核心组件包括 Wallet、Control Plane、HTTP/Analytics Data Plane 和 SSO Bridge，并以 Eclipse Dataspace Protocol（DSP）、DID、VC、DCP、DCAT 和 ODRL 为主要标准基础。因此，本文以当前官方架构为准，旧版 IDS 架构仅作为历史背景，不作为当前组件描述。

---

## 2. 结论速览

| 问题 | 结论 |
|---|---|
| 哪个更接近协议研究？ | **TNO TSG**。其架构中心是 Participant 发现、Catalog、Contract Negotiation、Agreement、Transfer Process 以及控制面—数据面分离。 |
| 哪个更接近完整工程落地？ | **FIWARE DSC**。它把身份、信任、产品目录、订单、合同管理、策略授权、API 网关和真实数据服务组合成完整闭环。 |
| 哪个更适合讲 DSP？ | **TNO TSG Playground**。流程与 DSP 阶段一一对应，概念边界清楚。 |
| 哪个更适合做工程型课程项目？ | **FIWARE DSC**。展示范围更完整，但部署、配置和排错成本更高。 |
| 本项目应如何选择？ | **FIWARE 负责“跑通业务闭环”，TSG 负责“讲清协议机制”。** |

两者最核心的差别可以概括为：

> **TNO TSG 从“参与者如何按照标准协议发现、协商并交换数据”出发；FIWARE DSC 从“组织如何把数据包装成产品、完成身份认证、订购、授权并最终访问服务”出发。**

---

## 3. 定位与设计目标

| 维度 | TNO TSG | FIWARE DSC |
|---|---|---|
| 核心定位 | 标准驱动的 Participant Agent | 集成式数据空间连接器与业务交付平台 |
| 架构中心 | DSP Control Plane、Wallet、Data Plane | 身份、TM Forum 产品体系、合同管理、ODRL 授权、数据服务 |
| 主要研究对象 | Catalog、Dataset、Policy、Negotiation、Agreement、Transfer | ProductSpecification、ProductOffering、ProductOrder、Credential、Policy、API Access |
| 主要价值 | 协议机制、状态机、互操作性 | 企业业务闭环、安全链路、服务产品化 |
| 典型用户问题 | “协议消息和状态如何变化？” | “数据服务如何发布、销售、开通并受控访问？” |

### 3.1 TNO TSG 的关注点

TNO TSG 的 Control Plane 直接实现 Dataspace Protocol，负责：

```text
Participant / Registry discovery
        ↓
Catalog request
        ↓
Dataset、Distribution、DataService
        ↓
ODRL Offer
        ↓
Contract Negotiation
        ↓
Agreement
        ↓
Transfer Process
        ↓
Data Plane access
```

因此，研究 TSG 时最自然的问题包括：

- Catalog 请求和响应包含什么；
- Dataset、Distribution 和 DataService 如何关联；
- Provider 的 ODRL Offer 如何表达；
- Negotiation 的状态如何变化；
- Agreement 在什么条件下产生；
- Agreement 与 Transfer Process 为什么不是同一个对象；
- Control Plane 如何协调 Wallet 和 Data Plane；
- 不同 Participant Agent 实现能否互操作。

### 3.2 FIWARE DSC 的关注点

FIWARE DSC 的边界更宽，典型业务流程为：

```text
准备 NGSI-LD / REST / S3 数据服务
        ↓
创建 ProductSpecification
        ↓
创建 ProductOffering
        ↓
Consumer 发现产品
        ↓
注册 Consumer Organization
        ↓
创建 ProductOrder
        ↓
订单 completed
        ↓
Contract Management 处理事件
        ↓
配置可信身份与 ODRL Policy
        ↓
Consumer 获取 Token
        ↓
APISIX / OPA 执行授权
        ↓
访问 Scorpio 或其他后端 API
```

它关注的是：

> **身份体系 + 产品体系 + 商业订单 + 合同处理 + 服务级授权 + 实际数据访问。**

---

## 4. 总体组件边界

### 4.1 TNO TSG

```text
┌──────────────────────────────────┐
│ SSO Bridge                       │
│ 组织内部用户和组件 OAuth/OIDC 认证 │
├──────────────────────────────────┤
│ Wallet                           │
│ DID / VC / VP / Keys / OID4VC    │
├──────────────────────────────────┤
│ Control Plane                    │
│ Registry / Catalog / Negotiation │
│ Agreement / Policy / Transfer    │
├──────────────────────────────────┤
│ HTTP / Analytics Data Plane      │
│ 实际数据交换或分析工作流协调        │
├──────────────────────────────────┤
│ Backend API / Data Source        │
└──────────────────────────────────┘
```

边界特点：

- 以 Participant Agent 为中心；
- 协议控制面与实际数据交换面分离；
- Wallet 是一等核心组件；
- Data Plane 可替换、可扩展；
- Marketplace 和商业订单不是协议内核。

### 4.2 FIWARE DSC

```text
┌────────────────────────────────────┐
│ Marketplace / Portal               │
├────────────────────────────────────┤
│ TM Forum Product Management        │
│ Specification / Offering / Order   │
├────────────────────────────────────┤
│ Contract Management                │
├────────────────────────────────────┤
│ Identity and Trust                 │
│ Keycloak / VCVerifier / TIL        │
├────────────────────────────────────┤
│ ODRL Authorization                 │
│ APISIX / OPA / ODRL-PAP            │
├────────────────────────────────────┤
│ EDC / Dataspace Protocol           │
│ Catalog / Negotiation / Transfer   │
├────────────────────────────────────┤
│ Scorpio / NGSI-LD / REST / S3      │
└────────────────────────────────────┘
```

边界特点：

- 以组织级完整部署为中心；
- 产品目录、订单、身份、授权与数据服务集成；
- 既包含业务层流程，也可包含 DSP 协议流程；
- 组件更多，工程展示更丰富，但部署负担更大。

---

## 5. 各层详细比较

## 5.1 身份与信任

### TNO TSG

Wallet 负责参与者在数据空间中的数字身份，包括：

- DID 创建、解析与更新；
- 密钥管理与签名验证；
- VC 签发、存储和验证；
- VP 创建和验证；
- OID4VC 与 DCP 协议；
- Participant 身份生命周期。

SSO Bridge 则负责组织内部用户和软件组件的 OAuth 2.0 / OpenID Connect 登录。

因此，TSG 清楚区分：

```text
Wallet：组织在外部数据空间中的可验证身份
SSO Bridge：组织内部用户和组件的登录身份
```

### FIWARE DSC

FIWARE 将身份与信任拆分到多个组件：

- **Keycloak**：用户认证和 Credential 签发；
- **VCVerifier**：验证 VC/VP，并参与 Access Token 获取流程；
- **Credentials Config Service**：描述访问服务需要哪些 Credential；
- **Trusted Issuers List**：维护可信签发者与 Credential 类型；
- **DID 与密钥配置**：标识 Provider、Consumer 和 Trust Anchor。

### 差异

| TNO TSG | FIWARE DSC |
|---|---|
| 身份能力集中在完整 Wallet 中 | 身份能力分布在 Issuer、Verifier、配置服务和信任列表中 |
| 更适合讲 Participant SSI 身份体系 | 更适合讲 VC 如何转化成业务 API Token |
| 外部身份与内部 SSO 分界明确 | 认证链路更工程化、组件更多 |

---

## 5.2 Catalog 与产品目录

### TNO TSG

TSG 的 Catalog 是标准的数据空间 Catalog：

```text
Catalog
└── Dataset
    └── Distribution
        └── DataService
```

主要回答：

- 有哪些数据集；
- 数据集有哪些 Distribution；
- DataService 的访问方式是什么；
- Dataset 附带什么 ODRL Offer。

### FIWARE DSC

FIWARE 同时存在两个视角：

**业务产品视角：**

```text
ProductSpecification
→ ProductOffering
→ ProductOrder
→ ProductInventory / Service access
```

**DSP 协议视角：**

```text
DCAT Catalog
→ Dataset
→ Distribution
→ DataService
→ ODRL Offer
```

### 差异

- TSG 主要回答：“这个数据集如何通过标准协议被发现？”
- FIWARE 还回答：“这个数据服务如何被包装成商品、发布、订购和开通？”
- FIWARE 的 Catalog 边界更宽，但也更容易让初学者混淆业务 Catalog 与 DSP Catalog。

---

## 5.3 合同与状态机

### TNO TSG

TSG 的主线是 DSP 合同状态机：

```text
ODRL Offer
→ Contract Request
→ Negotiation
→ Agreement
→ Transfer Process
```

其中：

- **Agreement** 是双方协商完成后形成的使用合同；
- **Transfer Process** 是基于 Agreement 建立的具体数据交换会话；
- 因此 **Agreement ≠ Transfer Process**。

### FIWARE DSC

FIWARE 中可能同时存在两类过程。

**TM Forum 业务过程：**

```text
ProductOffering
→ Quote / ProductOrder
→ completed
→ Product / service activation
```

**DSP 协议过程：**

```text
DCAT Offer
→ Contract Negotiation
→ Agreement
→ Transfer Process
```

### 重要概念边界

```text
ProductOrder ≠ DSP Contract Negotiation
ProductOrder completed ≠ DSP Agreement
DSP Agreement ≠ Transfer Process
```

- ProductOrder 是业务订购对象；
- DSP Agreement 是协议层使用合同；
- Transfer Process 是协议层数据交换会话。

在本项目中，Contract Management 日志能证明订单完成事件被接收和处理，但不能仅凭该日志断言完整 DSP Negotiation、Agreement 和 Transfer Process 已全部自动完成。

---

## 5.4 授权与策略

### TNO TSG

策略主要贯穿：

- Dataset Offer；
- Contract Negotiation；
- Agreement；
- Control Plane policy evaluation；
- Transfer-level access control。

Control Plane 判断是否允许达成 Agreement、是否允许创建 Transfer；HTTP Data Plane 根据有效 Transfer 和访问 Token 执行数据访问。

### FIWARE DSC

FIWARE 显式使用 ABAC 组件链：

```text
APISIX = Policy Enforcement Point（PEP）
OPA = Policy Decision Point（PDP）
ODRL-PAP = Policy Administration / Retrieval Point（PAP/PRP）
```

授权判断可以使用：

- Token 中的 VC claims；
- HTTP 方法；
- 请求路径；
- 目标资源；
- 请求体或数据属性；
- 环境和上下文条件。

### 差异

- TSG 更关注：“根据 Agreement 和 Transfer，是否允许进行数据交换？”
- FIWARE 更关注：“当前 Token 对这个具体 HTTP 请求是否有权限？”
- FIWARE 的 API 网关、OPA 和 ODRL 策略链更适合展示 `401 / 403 / 200` 的服务级授权结果。

---

## 5.5 数据面

### TNO TSG

TSG 明确提供多个可替换 Data Plane：

- **HTTP Data Plane**：代理 API、文件、流式 HTTP 数据；
- **Analytics Data Plane**：协调多方分析、联邦分析或事件工作流；
- 未来可继续接入其他 Data Plane。

Control Plane 只协调协议与状态，Data Plane 负责实际交换。

### FIWARE DSC

FIWARE 更强调将现有数据服务纳入统一产品和授权体系，例如：

- Scorpio / NGSI-LD；
- REST API；
- S3；
- NGSIv2；
- Web Portal；
- 其他 HTTP 服务。

### 差异

| TNO TSG | FIWARE DSC |
|---|---|
| Data Plane 是独立且可替换的执行层 | 数据服务被集成进产品、身份与授权体系 |
| 适合研究“协议如何协调传输” | 适合研究“真实 API 如何产品化并受控暴露” |
| 控制面—数据面边界更显式 | 端到端业务和安全链更完整 |

---

## 5.6 Marketplace 与商业管理

### TNO TSG

TSG 的协议内核主要包含：

```text
Participant
Catalog
Dataset
Policy
Agreement
Transfer
```

可以在其上构建门户，但 Marketplace、收费、订单和库存并不是 TSG Control Plane 的核心职责。

### FIWARE DSC

FIWARE 的 TM Forum / Marketplace 体系可管理：

- Product Specification；
- Product Offering；
- Product Order；
- Product Inventory；
- Customer / Party；
- 服务生命周期与可选的计费、结算能力。

因此：

> **TSG 更接近参与者间协议基础设施；FIWARE 更接近数据产品交易、权限开通与服务交付平台。**

---

## 6. Building Energy 对象映射

| 业务概念 | TNO TSG | FIWARE DSC |
|---|---|---|
| 数据产品 | DCAT Dataset | ProductSpecification |
| 提供方式 | Distribution / DataService | ProductOffering + 数据服务引用 |
| 使用条件 | ODRL Offer | ProductSpecification/Offering 中的 Credential 与 ODRL Policy |
| 产品发现 | DSP Catalog | TM Forum Catalog / Marketplace，或 DSP Catalog |
| 消费申请 | Contract Request | ProductOrder，或 DSP Contract Request |
| 协商过程 | Contract Negotiation | 业务订购过程，或独立 DSP Negotiation |
| 最终协议 | Agreement | 业务订单/产品状态，或独立 DSP Agreement |
| 数据交换会话 | Transfer Process | DSP Transfer，或 Token 化 API 访问 |
| 实际 API | HTTP Data Plane Backend | Scorpio / NGSI-LD / REST / S3 |
| 身份 | TSG Wallet、DID、VC | Keycloak、VCVerifier、TIL、DID |
| 访问执行 | Control Plane + Data Plane | APISIX + OPA + ODRL-PAP |

---

## 7. 教学 Demo 适用性

| 教学维度 | TNO TSG | FIWARE DSC |
|---|---|---|
| DSP 协议教学 | **非常适合** | 适合，但容易被业务层干扰 |
| Catalog / Negotiation 状态机 | **非常清晰** | 同时存在 ProductOrder 等对象，概念较多 |
| Agreement 与 Transfer 区分 | **非常清晰** | 需要明确区分业务订单和 DSP 对象 |
| Control Plane / Data Plane | **边界清晰** | 支持，但整体组件链更复杂 |
| 数据产品商业流程 | 较弱 | **非常适合** |
| DID / VC 教学 | Wallet 集中，概念清楚 | 流程完整，但组件更分散 |
| API 授权教学 | Transfer 级安全清楚 | **APISIX / OPA / ODRL 更直观** |
| Marketplace 展示 | 非核心 | **产品与订单模型完整** |
| 快速体验 | **官方 Playground 可直接使用** | 本地 Quick Start 仍需部署 k3s 全栈 |
| 工程架构教学 | 中等到高 | **非常丰富** |
| 初学者认知负担 | 较低到中 | 中到高 |
| 部署与排错风险 | Playground 模式低 | 本地完整部署较高 |
| 课程扩展方向 | 协议、状态机、互操作 | 业务集成、安全治理、数据服务 |

### 7.1 为什么 TSG 更适合讲协议

TSG Playground 的操作基本与协议阶段一一对应：

| Playground 操作 | 协议概念 |
|---|---|
| Discover Participant | Registry / Participant discovery |
| Request Catalog | Catalog Protocol |
| View Dataset | DCAT Dataset / Distribution |
| Negotiate Contract | Contract Negotiation |
| View completed negotiation | Agreement |
| Request Transfer | Transfer Process |
| Execute request | HTTP Data Plane |

其优势是：

1. 不必先部署完整基础设施；
2. 协议对象和状态可直接观察；
3. Agreement 与 Transfer 分层清楚；
4. 不会被 ProductOrder、Customer、Marketplace 和库存管理分散注意力。

### 7.2 为什么 FIWARE 更适合讲完整业务闭环

FIWARE 可以展示：

```text
数据如何进入 Scorpio
→ 如何成为 ProductSpecification
→ 如何发布 ProductOffering
→ Consumer 如何注册和下单
→ 订单如何触发 Contract Management
→ Credential 和 ODRL Policy 如何配置
→ 匿名访问为何返回 401
→ 无权限访问为何返回 403
→ 有效 Token 如何获得 200 和数据
```

这更接近 API Marketplace、数据产品交付和真实企业系统集成。

---

## 8. 对 Building Energy 项目的具体建议

## 8.1 FIWARE 主线：回答“数据如何产品化并真正开通”

```text
BuildingEnergyReading
→ ProductSpecification
→ ProductOffering
→ Consumer Organization
→ ProductOrder
→ completed
→ Contract Management
→ Trusted Issuer / ODRL Policy
→ VC / Access Token
→ APISIX / OPA
→ 获取 BuildingEnergyReading
```

建议保留的证据：

- BuildingEnergyReading Entity ID；
- ProductSpecification ID；
- ProductOffering ID；
- Consumer Organization ID 和 DID；
- ProductOrder ID；
- 订单状态；
- Contract Management 日志；
- ODRL Policy；
- 匿名请求 `401`；
- 无权限请求 `403`（如适用）；
- 授权请求 `200`；
- 返回的建筑能耗 JSON。

## 8.2 TSG 辅线：回答“协议如何运行”

将相同场景映射为：

```text
Dataset:
Building Energy Consumption Dataset

Distribution:
JSON / NGSI-LD REST API

DataService:
Provider HTTP endpoint

ODRL Offer:
Only authorized participants may access
```

演示流程：

```text
Consumer 发现 Provider
→ 请求 Provider Catalog
→ 找到 Building Energy Dataset
→ 查看 Distribution 和 ODRL Offer
→ 发起 Contract Negotiation
→ 获得 Agreement
→ 请求 Transfer Process
→ HTTP Data Plane 调用后端 API
```

建议记录：

- Participant ID；
- Catalog ID；
- Dataset ID；
- Distribution / DataService；
- ODRL Offer；
- Negotiation ID 和状态历史；
- Agreement ID；
- Transfer ID；
- Transfer 状态；
- HTTP Data Plane 响应。

---

## 9. 最终判断

### 9.1 单纯作为数据空间协议教学 Demo

> **推荐 TNO TSG Playground。**

原因是：

- Catalog、Negotiation、Agreement 和 Transfer 顺序清楚；
- Participant Agent、Wallet、Control Plane 和 Data Plane 边界明确；
- 可以直接观察协议对象和状态；
- 不必先处理复杂 Kubernetes、Keycloak、Scorpio、APISIX、OPA 和数据库部署；
- 更适合解释“Connector/DSP 到底如何工作”。

### 9.2 作为完整工程型课程项目

> **推荐 FIWARE DSC。**

它能同时覆盖：

- 数据管理；
- 数据产品化；
- 身份与信任；
- 产品目录和商业订单；
- 合同处理；
- ODRL 授权；
- API Gateway；
- 实际数据访问。

但必须控制部署范围，否则课程容易变成 Kubernetes 和基础设施排错实验。

### 9.3 本项目的最佳组合

> **继续以 FIWARE DSC 作为主工程 Demo，以 TNO TSG 作为协议对照和教学解释工具。**

最准确的总结是：

> **TNO TSG 更接近协议、状态机和 Participant Agent 研究，其边界围绕 Wallet、DSP Control Plane 和可插拔 Data Plane；FIWARE DSC 的边界扩展到 TM Forum 产品目录、Marketplace、订单、身份认证、ODRL 授权和实际数据服务。讲 DSP 时选择 TSG，讲完整数据产品业务闭环时选择 FIWARE。对于 Building Energy 项目，FIWARE 负责“跑通”，TSG 负责“讲清楚”。**

---

## 参考资料

1. [TNO Security Gateway — Architecture](https://tsg.dataspac.es/docs/architecture/)
2. [TNO Security Gateway — Components](https://tsg.dataspac.es/docs/architecture/components/)
3. [TNO Security Gateway — Control Plane](https://tsg.dataspac.es/docs/apps/control-plane/)
4. [TNO Security Gateway — Playground](https://tsg.dataspac.es/docs/playground/)
5. [FIWARE Data Space Connector](https://github.com/FIWARE/data-space-connector)
6. [FIWARE Business API Ecosystem](https://github.com/FIWARE-TMForum/Business-API-Ecosystem)
7. [ODRL-PAP](https://github.com/wistefan/odrl-pap)
