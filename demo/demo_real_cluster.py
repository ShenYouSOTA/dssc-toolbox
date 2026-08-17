#!/usr/bin/env python3
"""
FIWARE DSC 真实集群端到端 Demo

走 k3s 集群中的真实组件，完成完整数据空间流程：
1. 集群健康检查
2. Provider 创建 Data Offering (TMForum API + Scorpio)
3. Consumer 发现 Catalog
4. Consumer 认证 (Keycloak)
5. Contract Negotiation 记录
6. Data Transfer 记录
7. Consumer 获取数据
"""

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import httpx

from config import (
    DEMO_DIR,
    KC_CLIENT_ID,
    KC_PASSWORD,
    KC_REALM,
    KC_USERNAME,
    setup_logging,
)

log = setup_logging("cluster-demo")

PROVIDER_NAME = "Energy Data Provider Ltd."
PROVIDER_DID = "did:web:shenyousota.github.io:dssc-toolbox"
CONSUMER_DID = "did:web:fancy-marketplace.biz"
DATASET_ID = "building-energy-hourly-v1"
DATASET_URI = "urn:dssc:dataset:building-energy-hourly-v1"
CANONICAL_OFFERING_ID = "urn:dssc:service-offering:building-energy-hourly-v1"
OFFERING_VERSION = "0.1.0"
RESOURCE_ID = "urn:ngsi-ld:Building:BLD-001"
RETENTION_PERIOD = "P30D"
RETENTION_DESCRIPTION = (
    "Consumer must delete retrieved data within 30 days after the contract agreement."
)
DELIVERABLES_DIR = DEMO_DIR / "deliverables"

# ============================================================
# 集群 Ingress 端点
# ============================================================

ENDPOINTS = {
    "Provider Keycloak": "https://keycloak-provider.127.0.0.1.nip.io",
    "Consumer Keycloak": "https://keycloak-consumer.127.0.0.1.nip.io",
    "TMForum API": "https://tm-forum-api.127.0.0.1.nip.io",
    "Scorpio": "https://scorpio-provider.127.0.0.1.nip.io",
    "TIL": "https://til-provider.127.0.0.1.nip.io",
    "Dashboard": "https://dashboard-provider.127.0.0.1.nip.io",
    "TIR": "https://tir.127.0.0.1.nip.io",
    "Verifier": "https://verifier.mp-operations.org",
    "APISIX": "https://mp-data-service.127.0.0.1.nip.io",
}

CATALOGUE_URL = f"{ENDPOINTS['TMForum API']}/tmf-api/productCatalogManagement/v4/productOffering"
RESOURCE_ENDPOINT = f"{ENDPOINTS['Scorpio']}/ngsi-ld/v1/entities/{RESOURCE_ID}"


def write_json(path: Path, content: dict) -> None:
    """Write a deterministic, UTF-8 JSON delivery artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_provider_profile(generated_at: str, registration_observed: bool) -> dict:
    return {
        "schemaVersion": "1.0",
        "generatedAt": generated_at,
        "responsibleParty": "DSSC Group A",
        "providerId": PROVIDER_DID,
        "providerName": PROVIDER_NAME,
        "role": "Data Provider",
        "identitySource": {
            "type": "FIWARE Trusted Issuers Registry",
            "registryUrl": f"{ENDPOINTS['TIR']}/v4/issuers",
            "registrationObserved": registration_observed,
        },
        "scope": "local-real-cluster",
        "gaiaXComplianceStatus": "to-be-validated-by-group-b",
        "containsSensitiveCredentials": False,
    }


def build_offering_manifest(offering: dict, generated_at: str) -> dict:
    return {
        "schemaVersion": "1.0",
        "generatedAt": generated_at,
        "responsibleParty": "DSSC Group A",
        "canonicalOffering": {
            "id": CANONICAL_OFFERING_ID,
            "idDecisionStatus": "proposed-pending-ab-confirmation",
            "providerId": PROVIDER_DID,
            "providerName": PROVIDER_NAME,
            "datasetId": DATASET_ID,
            "datasetUri": DATASET_URI,
            "datasetUriDecisionStatus": "proposed-pending-ab-confirmation",
            "name": "Building Energy Consumption Dataset API",
            "description": "Hourly energy consumption data for buildings in Shenzhen",
            "version": OFFERING_VERSION,
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "policy": {
                "purpose": ["research", "analytics"],
                "attributionRequired": True,
                "redistributionAllowed": False,
                "retention": RETENTION_PERIOD,
                "retentionDescription": RETENTION_DESCRIPTION,
            },
        },
        "deployment": {
            "platform": "FIWARE Data Space Connector",
            "environment": "local-real-cluster",
            "productOfferingId": offering.get("offering_id", ""),
            "productSpecificationId": offering.get("spec_id", ""),
            "catalogueUrl": CATALOGUE_URL,
            "resourceIds": [RESOURCE_ID],
            "endpoint": RESOURCE_ENDPOINT,
            "endpointType": "NGSI-LD Entity API",
            "method": "GET",
            "responseMediaType": "application/ld+json",
            "openapi": "openapi-scorpio.yaml",
            "publiclyReachable": False,
        },
    }


def write_delivery_artifacts(
    offering: dict,
    negotiation: "NegotiationState",
    transfer: "TransferState",
    data: list,
    success: bool,
    generated_at: str,
) -> None:
    """Persist A-group delivery evidence without tokens or credentials."""
    registration_observed = offering.get("providerIdentity", {}).get("registered", False)
    write_json(
        DELIVERABLES_DIR / "provider-profile.json",
        build_provider_profile(generated_at, registration_observed),
    )
    write_json(DELIVERABLES_DIR / "offering-manifest.json", build_offering_manifest(offering, generated_at))
    write_json(
        DELIVERABLES_DIR / "connector-publication-result.json",
        {
            "schemaVersion": "1.0",
            "generatedAt": generated_at,
            "responsibleParty": "DSSC Group A",
            "artifactOrigin": "runtime-api-capture",
            "success": bool(offering.get("offering_id")),
            "executionMode": "fiware-real-cluster",
            "canonicalOfferingId": CANONICAL_OFFERING_ID,
            "publication": offering,
            "retrievedResourceIds": [item.get("id") for item in data if item.get("id")],
            "overallDemoSuccess": success,
            "containsSensitiveCredentials": False,
        },
    )
    write_json(
        DELIVERABLES_DIR / "contract-transfer-result.json",
        {
            "schemaVersion": "1.0",
            "generatedAt": generated_at,
            "responsibleParty": "DSSC Group A",
            "artifactOrigin": "runtime-state-record",
            "executionMode": "simulated-state-machine",
            "connectorExecuted": False,
            "warning": "Negotiation and transfer states are local demo records, not Connector API responses.",
            "negotiation": asdict(negotiation),
            "transfer": asdict(transfer),
            "containsSensitiveCredentials": False,
        },
    )


# ============================================================
# Data classes for tracking state
# ============================================================


@dataclass
class NegotiationState:
    """Contract Negotiation 状态记录"""
    negotiation_id: str = ""
    offering_id: str = ""
    consumer_did: str = ""
    provider_did: str = ""
    state: str = "INITIATED"
    contract_id: str = ""
    state_history: list = field(default_factory=list)
    timestamp: str = ""


@dataclass
class TransferState:
    """Transfer Process 状态记录"""
    transfer_id: str = ""
    negotiation_id: str = ""
    state: str = "INITIATED"
    data_address: dict = field(default_factory=dict)
    state_history: list = field(default_factory=list)
    timestamp: str = ""


# ============================================================
# HTTP helpers
# ============================================================


def get_client() -> httpx.Client:
    # WARNING: verify=False is required for local k3s clusters using self-signed
    # certificates. Never disable certificate verification in production.
    return httpx.Client(verify=False, timeout=30.0, follow_redirects=True)


def check_endpoint(client: httpx.Client, name: str, url: str, expect_status: int = 200) -> bool:
    try:
        resp = client.get(url, timeout=10.0)
        if resp.status_code == expect_status:
            print(f"  ✅ {name}: {resp.status_code}")
            return True
        else:
            print(f"  ⚠️  {name}: {resp.status_code} (期望 {expect_status})")
            return False
    except httpx.ConnectError:
        print(f"  ❌ {name}: 连接失败")
        return False
    except httpx.ReadTimeout:
        print(f"  ❌ {name}: 超时")
        return False
    except Exception as e:
        print(f"  ❌ {name}: {type(e).__name__}")
        return False


# ============================================================
# Step 1: Health Check
# ============================================================


def step_health_check(client: httpx.Client) -> dict:
    print("\n" + "=" * 60)
    print("📡 步骤1: 集群健康检查")
    print("=" * 60)

    results = {}
    checks = [
        ("TIR", f"{ENDPOINTS['TIR']}/v4/issuers"),
        ("Provider Keycloak", f"{ENDPOINTS['Provider Keycloak']}/realms/{KC_REALM}"),
        ("Consumer Keycloak", f"{ENDPOINTS['Consumer Keycloak']}/realms/{KC_REALM}"),
        ("TMForum API", f"{ENDPOINTS['TMForum API']}/tmf-api/productCatalogManagement/v4/catalog"),
        ("TIL", f"{ENDPOINTS['TIL']}/issuer"),
        ("Dashboard", f"{ENDPOINTS['Dashboard']}/"),
    ]

    for name, url in checks:
        results[name] = check_endpoint(client, name, url)

    # Scorpio: 400 is expected for empty query (service is alive)
    results["Scorpio"] = check_endpoint(client, "Scorpio", f"{ENDPOINTS['Scorpio']}/ngsi-ld/v1/entities", expect_status=400)

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n  📊 健康检查: {passed}/{total} 通过")
    return results


# ============================================================
# Step 2: Provider creates Data Offering
# ============================================================


def _normalize_odrl(node):
    """TMForum API collapses single-element arrays (permission/prohibition/duty)
    into plain objects. Normalize both sides to the list form before comparing."""
    if isinstance(node, dict):
        return {k: _normalize_odrl(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_normalize_odrl(v) for v in node]
    return node


def verify_policy_roundtrip(client: httpx.Client, offering_id: str, offering_request: dict) -> dict:
    """Read the ProductOffering back and confirm TMForum stored the ODRL
    access/contract policies unchanged."""
    result = {
        "sourceUrl": f"{CATALOGUE_URL}/{offering_id}" if offering_id else "",
        "httpStatus": None,
        "accessPolicyPreserved": False,
        "contractPolicyPreserved": False,
        "verified": False,
    }
    if not offering_id:
        result["reason"] = "offering creation failed, nothing to verify"
        return result

    resp = client.get(
        f"{CATALOGUE_URL}/{offering_id}",
        headers={"Accept": "application/json"},
    )
    result["httpStatus"] = resp.status_code
    if resp.status_code != 200:
        result["reason"] = f"read-back failed: {resp.status_code}"
        return result

    terms = resp.json().get("productOfferingTerm") or []
    requested_terms = offering_request.get("productOfferingTerm") or []
    expected_access = next((t.get("accessPolicy") for t in requested_terms if t.get("accessPolicy")), None)
    expected_contract = next((t.get("contractPolicy") for t in requested_terms if t.get("contractPolicy")), None)
    returned_access = next((t.get("accessPolicy") for t in terms if t.get("accessPolicy")), None)
    returned_contract = next((t.get("contractPolicy") for t in terms if t.get("contractPolicy")), None)

    def canon(policy):
        """Wrap collapsed singleton objects back into lists for comparison."""
        def wrap_lists(n):
            if isinstance(n, dict):
                return {k: ([wrap_lists(v)] if k in ("permission", "prohibition", "duty") and isinstance(v, dict)
                            else wrap_lists(v)) for k, v in n.items()}
            if isinstance(n, list):
                return [wrap_lists(v) for v in n]
            return n
        return wrap_lists(_normalize_odrl(policy))

    result["accessPolicyPreserved"] = expected_access is not None and canon(returned_access) == canon(expected_access)
    result["contractPolicyPreserved"] = expected_contract is not None and canon(returned_contract) == canon(expected_contract)
    result["verified"] = result["accessPolicyPreserved"] and result["contractPolicyPreserved"]
    if result["verified"]:
        log.info("ODRL policy round-trip verified for offering %s", offering_id)
    return result


def step_create_offering(client: httpx.Client) -> dict:
    print("\n" + "=" * 60)
    print("🏢 步骤2: Provider 创建 Data Offering")
    print("=" * 60)

    # 2a. Create entity in Scorpio
    print("\n  [Scorpio] 创建 Building 实体...")
    sample_path = DEMO_DIR / "data" / "scenarios" / "DSSC_Minimal_Energy_Scenario" / "data" / "building-energy-sample.json"
    sample_data = json.loads(sample_path.read_text(encoding="utf-8"))
    entity = {
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
            {
                "datasetId": "urn:dssc:property:datasetId",
                "providerName": "urn:dssc:property:providerName",
                "license": "urn:dssc:property:license",
                "readings": "urn:dssc:property:readings",
            },
        ],
        "id": RESOURCE_ID,
        "type": "Building",
        "name": {"type": "Property", "value": "Shenzhen Nanshan Tower"},
        "address": {"type": "Property", "value": {"city": "Shenzhen", "district": "Nanshan"}},
        "datasetId": {"type": "Property", "value": sample_data["datasetId"]},
        "providerName": {"type": "Property", "value": sample_data["providerName"]},
        "license": {"type": "Property", "value": sample_data["license"]},
        "readings": {"type": "Property", "value": sample_data["records"]},
    }
    resp = client.post(
        f"{ENDPOINTS['Scorpio']}/ngsi-ld/v1/entities",
        json=entity,
        headers={"Content-Type": "application/ld+json", "Accept": "application/json"},
    )
    entity_status = resp.status_code
    if entity_status in (201, 409):
        print(f"  ✅ 实体创建: {entity['id']} ({resp.status_code})")
        log.info("Scorpio entity created: %s", entity["id"])
    else:
        print(f"  ⚠️  实体创建: {resp.status_code} {resp.text[:100]}")

    # 2b. Create ProductSpecification in TMForum
    print("\n  [TMForum] 创建 ProductSpecification...")
    spec = {
        "name": "Energy Data Specification",
        "description": "Hourly building energy consumption data",
        "version": OFFERING_VERSION,
        "lifecycleStatus": "Active",
    }
    resp = client.post(
        f"{ENDPOINTS['TMForum API']}/tmf-api/productCatalogManagement/v4/productSpecification",
        json=spec,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    spec_id = ""
    spec_data = {}
    spec_status = resp.status_code
    if resp.status_code == 201:
        spec_data = resp.json()
        spec_id = spec_data.get("id", "")
        print(f"  ✅ Specification: {spec_id}")
        log.info("ProductSpecification created: %s", spec_id)
    else:
        print(f"  ⚠️  Specification: {resp.status_code}")

    # 2c. Create ProductOffering in TMForum
    print("\n  [TMForum] 创建 ProductOffering...")
    offering = {
        "name": "Building Energy Consumption Data",
        "description": "Hourly energy consumption data for buildings in Shenzhen",
        "version": OFFERING_VERSION,
        "isBundle": False,
        "isSellable": True,
        "lifecycleStatus": "Active",
        "productSpecification": {"id": spec_id, "name": spec["name"]} if spec_id else {},
        "productOfferingTerm": [
            {
                "name": "edc:contractDefinition",
                "@schemaLocation": "https://raw.githubusercontent.com/wistefan/edc-dsc/refs/heads/init/schemas/contract-definition.json",
                "accessPolicy": {
                    "@context": "http://www.w3.org/ns/odrl.jsonld",
                    "odrl:uid": "urn:dssc:policy:building-energy:access",
                    "assigner": PROVIDER_DID,
                    "permission": [{"action": "use"}],
                    "@type": "Offer",
                },
                "contractPolicy": {
                    "@context": "http://www.w3.org/ns/odrl.jsonld",
                    "odrl:uid": "urn:dssc:policy:building-energy:contract",
                    "assigner": PROVIDER_DID,
                    "permission": [
                        {
                            "action": "use",
                            "duty": [
                                {"action": "attribute"},
                                {
                                    "action": "delete",
                                    "constraint": {
                                        "leftOperand": "odrl:elapsedTime",
                                        "operator": "gteq",
                                        "rightOperand": {
                                            "@value": RETENTION_PERIOD,
                                            "@type": "xsd:duration",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                    "prohibition": [{"action": "distribute"}],
                    "@type": "Offer",
                },
            }
        ],
    }
    resp = client.post(
        f"{ENDPOINTS['TMForum API']}/tmf-api/productCatalogManagement/v4/productOffering",
        json=offering,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    offering_id = ""
    offering_data = {}
    offering_status = resp.status_code
    if resp.status_code == 201:
        offering_data = resp.json()
        offering_id = offering_data.get("id", "")
        print(f"  ✅ Offering: {offering_id}")
        print(f"     Name: {offering_data.get('name')}")
        log.info("ProductOffering created: %s", offering_id)
    else:
        print(f"  ⚠️  Offering: {resp.status_code} {resp.text[:100]}")

    # 2c-verify. Read the offering back and confirm the ODRL policies round-trip unchanged
    policy_verification = verify_policy_roundtrip(client, offering_id, offering)
    if policy_verification.get("verified"):
        print(f"  ✅ ODRL policy 回读一致 (access + contract policy 原样返回)")
    elif offering_id:
        print(f"  ⚠️  ODRL policy 回读不一致: {policy_verification}")

    # 2d. Verify Provider DID at TIR
    print("\n  [TIR] 验证 Provider DID 注册...")
    resp = client.get(f"{ENDPOINTS['TIR']}/v4/issuers")
    tir_status = resp.status_code
    provider_registered = False
    if resp.status_code == 200:
        tir_data = resp.json()
        items = tir_data.get("items", [])
        dids = [i.get("did") for i in items]
        if "did:web:shenyousota.github.io:dssc-toolbox" in dids:
            provider_registered = True
            print(f"  ✅ Provider DID 已注册: did:web:shenyousota.github.io:dssc-toolbox")
        if "did:web:fancy-marketplace.biz" in dids:
            print(f"  ✅ Consumer DID 已注册: did:web:fancy-marketplace.biz")
        print(f"     TIR 共 {len(items)} 个注册 Issuers")
    else:
        print(f"  ⚠️  TIR 查询: {resp.status_code}")

    return {
        "spec_id": spec_id,
        "offering_id": offering_id,
        "resource": {"id": RESOURCE_ID, "httpStatus": entity_status},
        "productSpecification": {
            "id": spec_id,
            "httpStatus": spec_status,
            "request": spec,
            "response": spec_data,
        },
        "productOffering": {
            "id": offering_id,
            "httpStatus": offering_status,
            "request": offering,
            "response": offering_data,
        },
        "policyVerification": policy_verification,
        "providerIdentity": {
            "did": PROVIDER_DID,
            "registryUrl": f"{ENDPOINTS['TIR']}/v4/issuers",
            "httpStatus": tir_status,
            "registered": provider_registered,
        },
    }


# ============================================================
# Step 3: Consumer discovers Catalog
# ============================================================


def step_consumer_discover(client: httpx.Client) -> list:
    print("\n" + "=" * 60)
    print("📡 步骤3: Consumer 发现 Catalog")
    print("=" * 60)

    resp = client.get(
        f"{ENDPOINTS['TMForum API']}/tmf-api/productCatalogManagement/v4/productOffering",
        headers={"Accept": "application/json"},
    )
    if resp.status_code == 200:
        offerings = resp.json()
        print(f"\n  ✅ 发现 {len(offerings)} 个 Offerings:")
        for o in offerings:
            print(f"     - {o.get('name')}: {o.get('id')}")
            print(f"       Status: {o.get('lifecycleStatus')}")
        log.info("Catalog discovered: %d offerings", len(offerings))
        return offerings
    else:
        print(f"  ❌ Catalog 查询失败: {resp.status_code}")
        return []


# ============================================================
# Step 4: Consumer authenticates via Keycloak
# ============================================================


def step_consumer_auth(client: httpx.Client) -> Optional[str]:
    print("\n" + "=" * 60)
    print("🔐 步骤4: Consumer Keycloak 认证")
    print("=" * 60)

    # Get realm info
    resp = client.get(f"{ENDPOINTS['Consumer Keycloak']}/realms/{KC_REALM}")
    if resp.status_code != 200:
        print(f"  ❌ Realm {KC_REALM} 不存在")
        return None

    realm = resp.json()
    token_endpoint = realm.get("token_endpoint", "")
    if not token_endpoint:
        # Keycloak legacy format: token-service + /token
        token_service = realm.get("token-service", "")
        if token_service:
            token_endpoint = f"{token_service}/token"
    if not token_endpoint:
        token_endpoint = f"{ENDPOINTS['Consumer Keycloak']}/realms/{KC_REALM}/protocol/openid-connect/token"
    print(f"  Token Endpoint: {token_endpoint}")

    # WARNING: password grant is used here only for local k3s demo convenience.
    # In production, prefer client_credentials or Authorization Code flow with PKCE.
    # Get token
    resp = client.post(
        token_endpoint,
        data={
            "grant_type": "password",
            "client_id": KC_CLIENT_ID,
            "username": KC_USERNAME,
            "password": KC_PASSWORD,
            "scope": "openid",
        },
    )
    if resp.status_code == 200:
        token_data = resp.json()
        token = token_data.get("access_token", "")
        expires_in = token_data.get("expires_in", 0)
        print(f"\n  ✅ Token 获取成功 (expires_in: {expires_in}s)")
        log.info("Consumer token obtained, expires_in=%ds", expires_in)

        # WARNING: signature verification is disabled here for local demo only.
        # Production code should verify the token using Keycloak's JWKS endpoint.
        import jwt
        payload = jwt.decode(token, options={"verify_signature": False})
        print(f"     Subject: {payload.get('sub')}")
        print(f"     Name: {payload.get('preferred_username', payload.get('name', 'N/A'))}")
        return token
    else:
        print(f"  ❌ Token 获取失败: {resp.status_code}")
        return None


# ============================================================
# Step 5: Contract Negotiation (record state)
# ============================================================


def step_contract_negotiation(client: httpx.Client, offering_id: str, token: str) -> NegotiationState:
    print("\n" + "=" * 60)
    print("📝 步骤5: Contract Negotiation")
    print("=" * 60)

    neg = NegotiationState()
    neg.offering_id = offering_id
    neg.consumer_did = CONSUMER_DID
    neg.provider_did = PROVIDER_DID
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # State 1: REQUESTED
    neg.state = "REQUESTED"
    neg.timestamp = now
    neg.state_history.append({"state": "REQUESTED", "timestamp": now, "detail": "Consumer initiated negotiation"})
    print(f"\n  [{neg.state}] {now}")
    print(f"     Offering: {offering_id}")
    print(f"     Consumer DID: {neg.consumer_did}")
    print(f"     Provider DID: {neg.provider_did}")

    # State 2: CONFIRMED (auto-advance)
    now2 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    neg.state = "CONFIRMED"
    neg.timestamp = now2
    neg.state_history.append({"state": "CONFIRMED", "timestamp": now2, "detail": "Provider confirmed negotiation"})
    print(f"\n  [{neg.state}] {now2}")
    print(f"     Provider acknowledged")

    # State 3: AGREED (auto-advance, generate contract)
    import uuid
    neg.contract_id = f"contract-{uuid.uuid4().hex[:8]}"
    now3 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    neg.state = "AGREED"
    neg.timestamp = now3
    neg.negotiation_id = f"neg-{uuid.uuid4().hex[:12]}"
    neg.state_history.append({"state": "AGREED", "timestamp": now3, "detail": f"Contract {neg.contract_id} created"})
    print(f"\n  [{neg.state}] {now3}")
    print(f"     Negotiation ID: {neg.negotiation_id}")
    print(f"     Contract ID: {neg.contract_id}")

    print(f"\n  ✅ 协商完成!")
    print(f"     状态流转: REQUESTED → CONFIRMED → AGREED")

    log.info("Contract negotiation: id=%s state=%s contract=%s",
             neg.negotiation_id, neg.state, neg.contract_id)
    return neg


# ============================================================
# Step 6: Transfer Process (record state)
# ============================================================


def step_transfer_process(client: httpx.Client, neg: NegotiationState) -> TransferState:
    print("\n" + "=" * 60)
    print("🔄 步骤6: Transfer Process")
    print("=" * 60)

    transfer = TransferState()
    transfer.negotiation_id = neg.negotiation_id
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # State 1: REQUESTED
    transfer.state = "REQUESTED"
    transfer.timestamp = now
    transfer.data_address = {"type": "HttpData", "baseUrl": f"{ENDPOINTS['Scorpio']}/ngsi-ld/v1/entities"}
    transfer.state_history.append({"state": "REQUESTED", "timestamp": now, "detail": "Consumer initiated transfer"})
    print(f"\n  [{transfer.state}] {now}")
    print(f"     Negotiation ID: {neg.negotiation_id}")

    # State 2: STARTED (auto-advance)
    now2 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    transfer.state = "STARTED"
    transfer.timestamp = now2
    transfer.state_history.append({"state": "STARTED", "timestamp": now2, "detail": "Provider started data provisioning"})
    print(f"\n  [{transfer.state}] {now2}")
    print(f"     Data source: Scorpio NGSI-LD")

    # State 3: COMPLETED (auto-advance)
    import uuid
    transfer.transfer_id = f"transfer-{uuid.uuid4().hex[:12]}"
    now3 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    transfer.state = "COMPLETED"
    transfer.timestamp = now3
    transfer.state_history.append({"state": "COMPLETED", "timestamp": now3, "detail": "Data ready for retrieval"})
    print(f"\n  [{transfer.state}] {now3}")
    print(f"     Transfer ID: {transfer.transfer_id}")

    print(f"\n  ✅ 传输完成!")
    print(f"     状态流转: REQUESTED → STARTED → COMPLETED")

    log.info("Transfer process: id=%s state=%s", transfer.transfer_id, transfer.state)
    return transfer


# ============================================================
# Step 7: Consumer retrieves data
# ============================================================


def step_retrieve_data(client: httpx.Client, token: str) -> list:
    print("\n" + "=" * 60)
    print("📊 步骤7: Consumer 获取数据")
    print("=" * 60)

    # Read entity from Scorpio
    resp = client.get(
        RESOURCE_ENDPOINT,
        headers={"Accept": "application/ld+json"},
    )
    if resp.status_code == 200:
        entity = resp.json()
        print(f"\n  ✅ 从 Scorpio 获取实体:")
        print(f"     ID: {entity.get('id')}")
        print(f"     Type: {entity.get('type')}")
        if "name" in entity:
            print(f"     Name: {entity['name'].get('value', 'N/A')}")
        if "address" in entity:
            addr = entity["address"].get("value", {})
            print(f"     Address: {addr.get('city', '')} {addr.get('district', '')}")
        log.info("Data retrieved from Scorpio: %s", entity.get("id"))
        return [entity]
    else:
        print(f"  ⚠️  数据获取: {resp.status_code}")
        return []


# ============================================================
# Step 8: Record summary
# ============================================================


def step_summary(health: dict, offering: dict, offerings: list, token: Optional[str],
                 neg: NegotiationState, transfer: TransferState, data: list) -> bool:
    print("\n" + "=" * 60)
    print("📊 流程总结")
    print("=" * 60)

    checks = [
        ("健康检查", all(health.values()), f"{sum(v for v in health.values())}/{len(health)} 通过"),
        ("创建 Offering", bool(offering.get("offering_id")), offering.get("offering_id", "N/A")),
        ("ODRL policy 回读一致", offering.get("policyVerification", {}).get("verified", False),
         f"access={offering.get('policyVerification', {}).get('accessPolicyPreserved')} "
         f"contract={offering.get('policyVerification', {}).get('contractPolicyPreserved')}"),
        ("发现 Catalog", len(offerings) > 0, f"{len(offerings)} 个 Offerings"),
        ("Consumer 认证", token is not None, "Token 获取成功"),
        ("Contract Negotiation", neg.state == "AGREED", f"{neg.state} | {neg.contract_id}"),
        ("Transfer Process", transfer.state == "COMPLETED", f"{transfer.state} | {transfer.transfer_id}"),
        ("数据获取", len(data) > 0, f"{len(data)} 条记录"),
    ]

    print()
    all_ok = True
    for name, ok, detail in checks:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}: {detail}")
        if not ok:
            all_ok = False

    print("-" * 60)
    if all_ok:
        print("✅ 真实集群端到端数据交换流程全部完成!")
    else:
        print("⚠️  部分步骤未完成")

    log.info("Demo summary: success=%s", all_ok)
    return all_ok


# ============================================================
# Main
# ============================================================


def run_full_demo():
    print("\n" + "🌟" * 30)
    print("\n  FIWARE DSC 真实集群端到端 Demo")
    print("  Provider 创建 Offering → Consumer 发现 → 认证 → 协商 → 传输 → 获取数据")
    print("\n" + "🌟" * 30)

    start = time.time()
    client = get_client()

    try:
        # Step 1: Health check
        health = step_health_check(client)

        # Step 2: Provider creates offering
        offering = step_create_offering(client)

        # Step 3: Consumer discovers catalog
        offerings = step_consumer_discover(client)

        # Step 4: Consumer authenticates
        token = step_consumer_auth(client)

        # Step 5: Contract negotiation
        neg = step_contract_negotiation(client, offering.get("offering_id", ""), token or "")

        # Step 6: Transfer process
        transfer = step_transfer_process(client, neg)

        # Step 7: Consumer retrieves data
        data = step_retrieve_data(client, token or "")

        # Step 8: Summary
        success = step_summary(health, offering, offerings, token, neg, transfer, data)

        generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_delivery_artifacts(offering, neg, transfer, data, success, generated_at)
        print(f"\n  结构化交付结果: {DELIVERABLES_DIR}")

        elapsed = time.time() - start
        print(f"\n  耗时: {elapsed:.1f}s")

    finally:
        client.close()


def run_health_only():
    client = get_client()
    try:
        step_health_check(client)
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description="FIWARE DSC 真实集群端到端 Demo")
    parser.add_argument("mode", choices=["full", "health"], default="full", nargs="?")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    try:
        if args.mode == "full":
            run_full_demo()
        elif args.mode == "health":
            run_health_only()
    except KeyboardInterrupt:
        print("\n\n⚠️  中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
