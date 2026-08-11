B 组与 A 组对接清单
对接目的
B 组需要使用 A 组在 Connector / Catalogue 中实际发布的 Provider、Data Offering 和 API 信息，生成或校对 Gaia-X LegalPerson 与 ServiceOffering credential，并确保合规凭证描述的对象与 A 组实际发布的对象完全一致。

一、请 A 组提供的数据
1. Provider 身份
- [x] Provider 名称
- [x] Provider 在 Connector / Catalogue 中的 participant ID
- [x] Provider DID（如已定义）
 Provider 主页或公开标识 URL（如有）
- [x] Provider 在 demo 中的角色
当前统一场景的预期值：

字段	预期值
Provider name	Energy Data Provider Ltd.
Provider DID	did:web:energy-provider.example.org（目前为占位值，需确认）
Role	Data Provider
2. Data Offering 信息
- [x] Offering ID
- [x] Offering 名称
- [x] Offering 描述
- [x] Offering 版本
- [x] Catalogue / Connector 中的 Offering URL
- [x] Offering 发布状态
- [x] Dataset ID
 Dataset URL 或资源标识符
- [x] Connector asset/resource ID
当前统一场景的预期值：

字段	预期值
Offering name	Building Energy Consumption Dataset API
Dataset ID	building-energy-hourly-v1
3. API 与访问方式
- [x] 完整 endpoint URL
- [x] OpenAPI 文件
- [x] HTTP method
- [x] Content-Type / 数据格式
- [x] 访问方式，例如 API
- [x] 是否需要认证（已提供 Keycloak OIDC 信息；Scorpio 读取尚未绑定合同令牌）
- [x] 访问控制方式（已提供现状与边界）
- [x] Contract negotiation ID 与结果（已有模拟记录，非 Connector API 结果）
- [x] Transfer process ID 与结果（已有模拟记录，非 Connector API 结果）
当前统一场景的预期值：

字段	预期值
Endpoint	https://api.example.org/energy/buildings/hourly
Format	application/json
Access type	API
4. License、政策与条款
- [x] License 名称与 URL
 使用政策，例如 research-use-only
 访问限制
 是否允许再分发
 数据保留要求（如有）
 Connector 实际执行的合同或政策规则
二、B 组如何使用
A 组数据	B 组用途
Provider name	填入或校对 LegalPerson 名称
Participant ID / DID	写入 LegalPerson.credentialSubject.id
Participant ID / DID	写入 ServiceOffering.gx:providedBy
Offering ID	写入 ServiceOffering.credentialSubject.id
Offering name / description	写入 gx:name、gx:description
Dataset ID / URL	写入或关联 gx:aggregationOf
Endpoint、format、access type	描述 ServiceOffering 的数据访问方式
License / policy	写入 gx:termsAndConditions、gx:policy 等描述
Catalogue URL	在最终 demo 中关联实际发布结果
Negotiation / transfer 结果	串联“合规—协商—访问数据”的演示流程
三、必须共同确认的一致性
 A 组 Participant ID = B 组 LegalPerson.credentialSubject.id
 A 组 Participant ID = B 组 ServiceOffering.gx:providedBy
 A 组 Offering ID = B 组 ServiceOffering.credentialSubject.id
- [x] A、B 组使用相同的 Dataset ID
 OpenAPI、metadata、Connector 与 credential 中的 endpoint 一致
 A 组实际执行的 license / policy 与 B 组 credential 声明一致
四、建议交付文件
- [x] provider-profile.json
- [x] offering-manifest.json
- [x] openapi.yaml
- [x] connector-publication-result.json 或等效截图/记录
- [x] contract-transfer-result.json 或等效截图/记录（如有）
建议 offering-manifest.json 至少包含：

{
  "providerId": "did:web:energy-provider.example.org",
  "providerName": "Energy Data Provider Ltd.",
  "offeringId": "https://example.org/dssc-energy/service-offerings/building-energy-hourly-v1",
  "datasetId": "building-energy-hourly-v1",
  "name": "Building Energy Consumption Dataset API",
  "description": "Hourly electricity consumption data for demo buildings.",
  "endpointUrl": "https://api.example.org/energy/buildings/hourly",
  "format": "application/json",
  "accessType": "API",
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "policy": ["research-use-only"],
  "catalogueUrl": "待 A 组提供",
  "connectorAssetId": "待 A 组提供",
  "version": "待 A 组提供"
}
五、交付验收
- [x] 所有 ID 均为最终值或明确标记为占位值
 文件注明版本、生成时间和负责人
- [x] Offering 已实际发布，或明确标记为 mock / planned
- [x] Endpoint 与 OpenAPI 可对应
 License 与 policy 没有相互矛盾
 未向 B 组传递任何私钥或敏感生产凭据
