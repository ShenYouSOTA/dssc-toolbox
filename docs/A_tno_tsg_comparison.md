# FIWARE Data Space Connector vs TNO Trusted Secure Gateway Comparison

## 1. Introduction

### Background of Connector Technologies

Data Space Connectors provide the technical foundation for organizations to participate in sovereign data sharing environments. A connector typically sits between an organization's internal data systems and external data-space participants. It is responsible for functions such as identity, authentication, authorization, policy enforcement, contract handling, and secure data exchange.

Different connector implementations emphasize different aspects of the data-space architecture.

The **FIWARE Data Space Connector (DSC)** is designed as an engineering-oriented data-space platform that integrates several technologies and ecosystem components, including FIWARE technologies, Eclipse Dataspace Connector (EDC), NGSI-LD, OID4VC, TM Forum APIs, ODRL-based policies, and marketplace-related services.

The **TNO Trusted Secure Gateway (TSG)** is a connector implementation developed by TNO that focuses more directly on secure and interoperable data-space communication. Its architecture is more modular and emphasizes data-space protocols, identity, policy enforcement, and secure data exchange.

### Purpose of Comparison

The purpose of this comparison is to analyze FIWARE DSC and TNO TSG from the following perspectives:

- Architecture and component organization
- Data exchange and communication workflow
- Contract and policy mechanisms
- Identity and trust mechanisms
- Deployment complexity
- Strengths and limitations
- Suitability for an energy-data-space scenario
- Suitability as a teaching and demonstration platform

The comparison particularly considers whether a connector is more suitable for **engineering-oriented data-space deployment** or for **understanding data-space protocols and connector concepts**.

---

# 2. Technology Overview

## 2.1 FIWARE Data Space Connector

### Architecture Overview

FIWARE DSC is a relatively comprehensive data-space platform rather than a single lightweight connector component.

Its architecture integrates multiple functional layers:

```text
+------------------------------------------------------+
|                  Marketplace / TM Forum              |
|        Product Catalog / Product Offering / Order    |
+------------------------------------------------------+
|              Contract Management / Policy            |
|              ODRL / OPA / Authorization              |
+------------------------------------------------------+
|             Dataspace Connector / EDC                |
|        Catalog / Contract / Transfer Processes       |
+------------------------------------------------------+
|          Identity and Credential Services             |
|       DID / VC / VP / Credential Verification        |
+------------------------------------------------------+
|                 Data Service Layer                    |
|          APISIX / Scorpio / NGSI-LD / APIs           |
+------------------------------------------------------+
|                Provider Data Sources                  |
|             Energy / IoT / Digital Twins             |
+------------------------------------------------------+
```

The FIWARE environment therefore covers both **data-space connectivity** and a number of surrounding business and infrastructure services.

### Main Characteristics

The main characteristics of FIWARE DSC include:

- Integration with FIWARE technologies and NGSI-LD.
- Integration with Eclipse Dataspace Connector technologies.
- Support for decentralized identity and verifiable credentials.
- Integration with TM Forum APIs for product catalog and ordering.
- Policy enforcement using technologies such as ODRL and OPA.
- Marketplace-oriented functionality.
- Support for digital-twin and IoT-oriented data.
- Kubernetes-based deployment for an integrated local environment.

This makes FIWARE DSC particularly suitable when the goal is to demonstrate how a data-space connector can be integrated into a broader enterprise or marketplace environment.

---

## 2.2 TNO Trusted Secure Gateway

### Architecture Overview

TNO TSG focuses more strongly on the connector and secure data-space communication layer.

A simplified conceptual architecture is:

```text
+---------------------------------------------+
|                TNO TSG                      |
|                                             |
|  +----------------+   +----------------+   |
|  | Identity /     |   | Policy /       |   |
|  | Wallet         |   | Security       |   |
|  +----------------+   +----------------+   |
|                                             |
|  +---------------------------------------+  |
|  |        Dataspace Protocol Layer       |  |
|  |     Catalog / Contract / Transfer     |  |
|  +---------------------------------------+  |
|                                             |
|  +---------------------------------------+  |
|  |          Data Plane                  |  |
|  |      HTTP / Analytics Data           |  |
|  +---------------------------------------+  |
+---------------------------------------------+
```

TSG is designed around the idea that secure data sharing should be implemented through clearly separated connector functions rather than embedding all marketplace and enterprise-management functionality into one platform.

### Main Characteristics

Important characteristics include:

- Strong focus on secure data-space communication.
- Modular connector architecture.
- Explicit separation between control-plane and data-plane functions.
- Identity and trust mechanisms.
- Policy-aware data exchange.
- Support for Dataspace Protocol concepts.
- Smaller functional scope compared with an integrated FIWARE marketplace environment.

Therefore, TNO TSG is particularly useful when studying the **technical and protocol-level behavior of a data-space connector**.

---

# 3. Architecture Comparison

## System Design

The two platforms have different architectural philosophies.

FIWARE DSC follows a relatively **integrated platform approach**. Multiple components required by an organization participating in a data space can be deployed together.

TNO TSG follows a more **connector-oriented and modular approach**. The connector itself focuses on secure communication and data-space functionality, while other services can remain separate.

The conceptual difference can be summarized as:

```text
FIWARE DSC

Business / Marketplace
        ↓
Contract / Policy
        ↓
Dataspace Connector
        ↓
Identity / Trust
        ↓
Data Services
        ↓
Data Sources
```

versus:

```text
TNO TSG

Identity / Trust
        ↓
Dataspace Protocol
        ↓
Connector
        ↓
Data Plane
        ↓
External Data System
```

FIWARE therefore exposes a broader **organizational platform**, while TNO TSG exposes a narrower **connector architecture**.

---

## Component Structure

| Aspect | FIWARE Data Space Connector | TNO TSG |
|---|---|---|
| Connector | EDC/FDSC-based connector components | TNO TSG connector |
| Identity | DID / VC / VP-oriented mechanisms | Wallet / identity-oriented mechanisms |
| Catalog | Dataspace catalog + marketplace catalog | Dataspace Protocol catalog |
| Contract | Dataspace contracts + marketplace concepts | Dataspace Protocol contract concepts |
| Ordering | TM Forum ProductOrder | Not primarily marketplace-oriented |
| Policy | ODRL / OPA-based mechanisms | Policy/security enforcement |
| Data layer | NGSI-LD / Scorpio / APIs | HTTP and other data-plane mechanisms |
| Marketplace | Integrated marketplace components | Outside the core connector |
| Deployment | Integrated Kubernetes environment | More modular deployment |

The major architectural difference is therefore the **scope of responsibility**.

FIWARE DSC extends beyond the connector itself and provides a wider set of services for a complete data-space environment.

TNO TSG concentrates more strongly on the connector and protocol layer.

---

## Communication Model

FIWARE DSC can involve several communication layers:

```text
Consumer
   |
   | Marketplace / TM Forum
   ↓
Product Offering
   |
   ↓
Product Order
   |
   ↓
Contract Management
   |
   ↓
Dataspace Connector
   |
   ↓
Data Service
   |
   ↓
NGSI-LD Entity
```

This allows a demonstration to connect a commercial/business transaction with a subsequent data exchange.

TNO TSG places greater emphasis on the data-space communication itself:

```text
Consumer Connector
        |
        | Catalog
        ↓
Provider Connector
        |
        | Contract
        ↓
Provider Connector
        |
        | Transfer
        ↓
Consumer Data Plane
```

Consequently, TSG provides a relatively direct way to demonstrate the concepts behind **catalog, contract, transfer, identity, and policy**.

---

# 4. Functional Comparison

## Data Exchange Workflow

### FIWARE DSC

A typical FIWARE-oriented workflow can include:

```text
1. Provider creates data
        ↓
2. Provider creates Product Specification
        ↓
3. Provider creates Product Offering
        ↓
4. Consumer discovers Product Offering
        ↓
5. Consumer Organization is registered
        ↓
6. Consumer creates ProductOrder
        ↓
7. ProductOrder becomes completed
        ↓
8. Contract Management processes the event
        ↓
9. Consumer obtains authorization
        ↓
10. Consumer accesses protected data
```

This workflow is useful because it demonstrates both:

- Business-level interaction
- Technical data-space exchange

For example, the Building Energy scenario can use a `BuildingEnergyReading` NGSI-LD entity as the protected data resource.

### TNO TSG

TSG focuses more directly on:

```text
1. Establish identity
        ↓
2. Discover data
        ↓
3. Negotiate / establish contract
        ↓
4. Apply policy
        ↓
5. Transfer data
        ↓
6. Enforce usage restrictions
```

The workflow is therefore closer to the conceptual structure of a data-space protocol.

---

## Contract Negotiation

FIWARE DSC combines technical contract mechanisms with marketplace and product-management concepts.

For example:

```text
ProductSpecification
        ↓
ProductOffering
        ↓
ProductOrder
        ↓
Contract Management
        ↓
Dataspace Contract
```

This makes the platform suitable for demonstrating how a data-space can connect **business transactions with technical contracts**.

TNO TSG places more emphasis on the data-space contract itself rather than on marketplace product ordering.

Therefore:

> FIWARE DSC provides a stronger business-to-technical workflow, while TNO TSG provides a more direct protocol-oriented contract workflow.

---

## Policy Enforcement

FIWARE DSC uses policy technologies such as ODRL and OPA to express and enforce access and usage policies.

The conceptual flow is:

```text
ODRL Policy
     ↓
Policy Decision
     ↓
Authorization
     ↓
Data Access
```

This is particularly useful for demonstrating data sovereignty.

TNO TSG also incorporates policy and security mechanisms, but the policy mechanism is more closely associated with connector-level secure data exchange.

Therefore, FIWARE is particularly useful when demonstrating the relationship between:

```text
Business agreement
        ↓
Policy
        ↓
Authorization
        ↓
Data access
```

while TNO TSG is useful when demonstrating:

```text
Protocol message
        ↓
Policy evaluation
        ↓
Secure transfer
```

---

## Trust Mechanisms

FIWARE DSC emphasizes decentralized identity technologies, including DID and Verifiable Credentials.

A simplified flow is:

```text
Issuer
   ↓
Verifiable Credential
   ↓
Consumer / Provider
   ↓
Credential Verification
   ↓
Authorized Dataspace Access
```

TNO TSG uses its own identity and trust mechanisms within its connector architecture.

The important distinction is not simply which technology is "better", but where identity is located architecturally:

- FIWARE integrates identity with marketplace, authorization, and data-space components.
- TNO TSG treats identity and secure communication as important parts of the connector architecture itself.

---

# 5. Deployment Comparison

## Deployment Approach

FIWARE DSC is commonly deployed as a relatively large integrated environment.

A local demonstration may involve:

```text
Kubernetes / k3s
    |
    +-- Marketplace
    +-- TM Forum APIs
    +-- Contract Management
    +-- Identity Services
    +-- Policy Services
    +-- Dataspace Connector
    +-- Scorpio
    +-- Data Service
```

This provides a realistic environment but also introduces considerable deployment complexity.

TNO TSG can be deployed in a more modular way, allowing the user to focus on the connector components required for the demonstration.

---

## Infrastructure Requirements

### FIWARE DSC

Advantages:

- Provides many components in one environment.
- Suitable for realistic integration testing.
- Suitable for demonstrating multiple technologies simultaneously.

Challenges:

- Relatively high resource requirements.
- Kubernetes configuration can be complicated.
- Many services must be understood simultaneously.
- Debugging can involve multiple components.

### TNO TSG

Advantages:

- Smaller conceptual footprint.
- Easier to isolate connector functionality.
- More suitable for protocol experiments.

Challenges:

- Some surrounding services may need to be configured separately.
- It may provide less marketplace functionality out of the box.

---

## Complexity

A rough conceptual comparison is:

```text
Deployment Complexity

FIWARE DSC
████████████████████
High

TNO TSG
██████████
Medium / Lower
```

The exact resource requirements depend on the selected deployment configuration, so this comparison should be understood as architectural rather than as a strict benchmark.

---

# 6. Strengths and Limitations

## FIWARE Data Space Connector

### Advantages

1. **Comprehensive ecosystem**

   FIWARE DSC combines identity, authorization, marketplace, contract management, dataspace connectivity, and data services.

2. **Strong NGSI-LD integration**

   This makes it particularly suitable for IoT, smart-city, and digital-twin scenarios.

3. **Business workflow integration**

   TM Forum APIs allow concepts such as Product Specification, Product Offering, and ProductOrder to be demonstrated.

4. **Good enterprise demonstration value**

   A complete workflow can show how data-space technologies interact with business processes.

### Limitations

1. **High complexity**

   There are many components to understand and configure.

2. **Large deployment footprint**

   A complete local deployment can require substantial computing resources.

3. **Protocol abstraction**

   Some underlying data-space concepts are hidden behind higher-level marketplace and platform components.

4. **Steeper learning curve**

   Beginners may need to understand Kubernetes, identity, policy, marketplace APIs, NGSI-LD, and dataspace components simultaneously.

---

## TNO TSG

### Advantages

1. **Clear connector architecture**

   Its architecture makes the role of a connector easier to isolate.

2. **Protocol-oriented design**

   It is useful for understanding catalog, contract, transfer, identity, and policy concepts.

3. **Modularity**

   Connector functionality and surrounding services can be separated.

4. **Good research value**

   Researchers can focus on secure data-space communication without necessarily deploying a complete marketplace platform.

### Limitations

1. **Less marketplace functionality**

   Compared with FIWARE DSC, TSG is less focused on TM Forum-style product management and marketplace workflows.

2. **Less emphasis on NGSI-LD**

   It is not primarily designed around FIWARE's NGSI-LD digital-twin ecosystem.

3. **Additional integration may be required**

   A complete business-oriented data-space environment may require external components.

---

# 7. Suitability for Energy Data Space Scenario

## Applicability Analysis

An energy data-space scenario typically contains:

```text
Energy Provider
       |
       ↓
Energy Data
       |
       ↓
Data Space Connector
       |
       ↓
Consumer
       |
       ↓
Energy Analytics
```

For the Building Energy scenario, an example data entity is:

```json
{
  "id": "urn:ngsi-ld:BuildingEnergyReading:demo",
  "type": "BuildingEnergyReading",
  "buildingId": "building-demo",
  "meterId": "meter-demo",
  "energyKWh": 128.4,
  "unit": "kWh"
}
```

### FIWARE DSC Suitability

FIWARE DSC is particularly strong for this scenario because energy data can naturally be represented using NGSI-LD.

The complete workflow can demonstrate:

```text
Building Energy Data
        ↓
NGSI-LD / Scorpio
        ↓
Data Service
        ↓
Dataspace Authorization
        ↓
Consumer
```

At the same time, the marketplace layer can represent the data product:

```text
Energy Dataset
      ↓
Product Specification
      ↓
Product Offering
      ↓
ProductOrder
```

Therefore, FIWARE DSC is well suited to an **end-to-end energy data marketplace demonstration**.

---

## TNO TSG Suitability

TNO TSG is more suitable when the main research question is:

> How can an energy provider securely exchange data with an authorized consumer through a data-space connector?

The demonstration can focus on:

```text
Provider
   ↓
Identity
   ↓
Catalog
   ↓
Contract
   ↓
Policy
   ↓
Secure Transfer
   ↓
Consumer
```

This makes TNO TSG particularly suitable for:

- Data-space protocol education
- Security research
- Connector architecture experiments
- Policy enforcement experiments
- Secure data exchange research

---

## Scenario-Based Evaluation

| Requirement | FIWARE DSC | TNO TSG |
|---|---:|---:|
| Energy data exchange | ★★★★★ | ★★★★☆ |
| NGSI-LD / digital twins | ★★★★★ | ★★☆☆☆ |
| Marketplace workflow | ★★★★★ | ★★☆☆☆ |
| Product ordering | ★★★★★ | ★☆☆☆☆ |
| Dataspace protocol learning | ★★★★☆ | ★★★★★ |
| Connector architecture research | ★★★★☆ | ★★★★★ |
| Policy research | ★★★★★ | ★★★★☆ |
| Identity research | ★★★★★ | ★★★★☆ |
| Deployment simplicity | ★★☆☆☆ | ★★★★☆ |
| Teaching beginners | ★★★☆☆ | ★★★★★ |
| Enterprise-style demonstration | ★★★★★ | ★★★★☆ |

---

# 8. Conclusion

FIWARE Data Space Connector and TNO Trusted Secure Gateway address different layers and priorities of data-space technology.

FIWARE DSC is better understood as a **broader data-space platform and ecosystem integration solution**. It combines dataspace connectivity with identity, authorization, policy, marketplace, product management, and NGSI-LD data services.

TNO TSG is closer to a **connector- and protocol-oriented architecture**. Its narrower scope makes it easier to study the fundamental mechanisms of secure data-space communication.

The main difference can therefore be summarized as:

```text
FIWARE DSC
= Data Space Connectivity
+ Identity
+ Policy
+ Marketplace
+ Product Management
+ NGSI-LD
+ Enterprise Integration
```

while:

```text
TNO TSG
= Connector
+ Dataspace Protocol
+ Identity / Trust
+ Policy
+ Secure Data Exchange
```

### Overall Recommendation

For an **enterprise-oriented energy data-space demonstration**, FIWARE DSC is the stronger choice because it can demonstrate the entire path from data-product creation and marketplace operations to authorization and actual NGSI-LD data exchange.

For **protocol research and teaching**, TNO TSG is generally more suitable because its smaller and more modular architecture makes the core concepts of connector-based data sharing easier to isolate and explain.

Therefore:

> **FIWARE DSC is better for demonstrating how a complete data-space ecosystem can be built and integrated, while TNO TSG is better for understanding how the connector and data-space protocols themselves work.**

For the current Building Energy project, FIWARE DSC is therefore appropriate as the **end-to-end demonstration platform**, while TNO TSG can serve as a useful **reference implementation for studying connector architecture, security, and data-space protocols**.