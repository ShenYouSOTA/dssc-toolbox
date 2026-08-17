"""
FIWARE DSC Data Exchange Demo - Provider Mock API

模拟数据提供方 (Energy Data Provider Ltd.) 的API服务，覆盖完整数据空间流程：
- /api/catalog/offerings - 数据发布 (创建 Data Offering)
- /api/catalog - 数据发现 (列出可用 offerings)
- /api/catalog/{id} - 查看 offering 详情 (含 metadata + contract policy)
- /api/contract-negotiations - 访问协商 (Contract Negotiation 状态机)
- /api/transfer-processes - 数据传输 (Transfer Process 状态机)
- /api/energy/buildings/hourly - 建筑能耗数据接口
- /auth/token - 认证接口
- /health - 健康检查
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import jwt
import yaml
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    DATASET_ID,
    DEFAULT_DATA_FILE,
    DEFAULT_METADATA_FILE,
    DEFAULT_OPENAPI_FILE,
    DEFAULT_SCENARIO,
    DEMO_CLIENTS,
    JWT_ALGORITHM,
    JWT_EXPIRY_HOURS,
    JWT_SECRET,
    PROVIDER_DID,
    PROVIDER_NAME,
    scenario_data_dir,
    scenario_metadata_dir,
    scenario_mock_api_dir,
    setup_logging,
)

log = setup_logging("provider")

# ============================================================
# Data Models - Auth
# ============================================================


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str
    grant_type: str = "client_credentials"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


# ============================================================
# Data Models - Offering
# ============================================================


class Policy(BaseModel):
    """Contract policy for an offering."""
    type: str  # "OPEN", "NEGOTIATE", "RESTRICTED"
    description: str
    license: str
    purpose: Optional[str] = None
    constraints: Optional[list[str]] = None


class DataOffering(BaseModel):
    """Data offering published by Provider."""
    offeringId: str
    datasetId: str
    title: str
    description: str
    providerName: str
    endpointUrl: str
    format: str
    frequency: str
    unit: str
    spatialCoverage: str
    temporalStart: str
    temporalEnd: str
    policy: Policy
    metadata: dict  # JSON-LD
    contractTemplate: dict  # OpenAPI spec
    createdAt: str
    status: str  # "ACTIVE", "INACTIVE"


# ============================================================
# Data Models - Contract Negotiation
# ============================================================


class NegotiationState(str, Enum):
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"
    AGREED = "AGREED"
    DECLINED = "DECLINED"
    ERROR = "ERROR"


class ContractNegotiationRequest(BaseModel):
    offeringId: str
    consumerDID: str
    providerDID: Optional[str] = None
    callbackUrl: Optional[str] = None


class ContractNegotiation(BaseModel):
    negotiationId: str
    offeringId: str
    consumerDID: str
    providerDID: str
    state: NegotiationState
    contractId: Optional[str] = None
    errorMessage: Optional[str] = None
    createdAt: str
    updatedAt: str
    stateHistory: list[dict]


# ============================================================
# Data Models - Transfer Process
# ============================================================


class TransferState(str, Enum):
    REQUESTED = "REQUESTED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class TransferProcessRequest(BaseModel):
    negotiationId: str
    dataAddress: Optional[dict] = None


class TransferProcess(BaseModel):
    transferId: str
    negotiationId: str
    offeringId: str
    state: TransferState
    dataAddress: Optional[dict] = None  # Consumer's data sink
    resourceAddress: Optional[dict] = None  # Provider's data source
    errorMessage: Optional[str] = None
    createdAt: str
    updatedAt: str
    stateHistory: list[dict]


# ============================================================
# Data Models - Energy
# ============================================================


class EnergyReading(BaseModel):
    buildingId: str
    meterId: str
    timestamp: str
    energyKWh: float
    unit: str
    location: dict


class EnergyDataset(BaseModel):
    datasetId: str
    providerName: str
    license: str
    records: list[EnergyReading]


# ============================================================
# In-Memory Stores
# ============================================================

offerings: dict[str, DataOffering] = {}
negotiations: dict[str, ContractNegotiation] = {}
transfers: dict[str, TransferProcess] = {}

# ============================================================
# Data Loading
# ============================================================


def load_sample_data(
    scenario: str | None = None,
    filename: str | None = None,
) -> dict:
    """Load sample energy data from JSON file.

    Args:
        scenario: Scenario name. Uses DEFAULT_SCENARIO when omitted.
        filename: Data payload filename. Uses DEFAULT_DATA_FILE when omitted.
    """
    data_file = scenario_data_dir(scenario) / (filename or DEFAULT_DATA_FILE)
    if data_file.exists():
        with open(data_file, "r") as f:
            return json.load(f)
    return {
        "datasetId": DATASET_ID,
        "providerName": PROVIDER_NAME,
        "license": "CC-BY-4.0",
        "records": [
            {
                "buildingId": "BLD-001",
                "meterId": "MTR-001",
                "timestamp": "2026-05-01T00:00:00+08:00",
                "energyKWh": 12.4,
                "unit": "kWh",
                "location": {"city": "Shenzhen", "district": "Nanshan"},
            }
        ],
    }


def load_metadata(
    scenario: str | None = None,
    filename: str | None = None,
) -> dict:
    """Load data product metadata from JSON-LD file.

    Args:
        scenario: Scenario name. Uses DEFAULT_SCENARIO when omitted.
        filename: Metadata filename. Uses DEFAULT_METADATA_FILE when omitted.
    """
    meta_file = scenario_metadata_dir(scenario) / (filename or DEFAULT_METADATA_FILE)
    if meta_file.exists():
        with open(meta_file, "r") as f:
            return json.load(f)
    return {}


def load_openapi_spec(
    scenario: str | None = None,
    filename: str | None = None,
) -> dict:
    """Load OpenAPI spec from YAML file.

    Args:
        scenario: Scenario name. Uses DEFAULT_SCENARIO when omitted.
        filename: OpenAPI contract filename. Uses DEFAULT_OPENAPI_FILE when omitted.
    """
    spec_file = scenario_mock_api_dir(scenario) / (filename or DEFAULT_OPENAPI_FILE)
    if spec_file.exists():
        with open(spec_file, "r") as f:
            return yaml.safe_load(f)
    return {}


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="Building Energy Consumption Dataset API",
    version="0.2.0",
    description="Mock Provider API for DSSC Toolbox - 支持数据发布、发现、协商、传输",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory client store (for demo)
VALID_CLIENTS = DEMO_CLIENTS

# ============================================================
# Auth Endpoints
# ============================================================


@app.post("/auth/token", response_model=TokenResponse)
async def get_token(request: TokenRequest):
    """OAuth2-style token endpoint. Simulates VCVerifier issuing JWT."""
    client = VALID_CLIENTS.get(request.client_id)
    if not client or client["secret"] != request.client_secret:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    payload = {
        "sub": request.client_id,
        "name": client["name"],
        "role": client["role"],
        "did": client["did"],
        "iss": "dssc-provider-verifier",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "scope": "read:energy-data",
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    log.info("Token issued for client=%s role=%s expires_in=%ds", request.client_id, client["role"], JWT_EXPIRY_HOURS * 3600)

    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=JWT_EXPIRY_HOURS * 3600,
    )


def verify_token(authorization: str) -> dict:
    """Verify JWT token and return payload."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ============================================================
# Data Publishing - Create Offering
# ============================================================


@app.post("/api/catalog/offerings", response_model=DataOffering)
async def create_offering(
    policy: Optional[Policy] = None,
    authorization: Optional[str] = Header(None),
):
    """
    Provider 发布 Data Offering。
    加载 metadata (JSON-LD) + contract template (OpenAPI) 创建 offering。
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")

    payload = verify_token(authorization)

    # Load external assets
    metadata = load_metadata()
    openapi_spec = load_openapi_spec()

    # Default policy
    if policy is None:
        policy = Policy(
            type="NEGOTIATE",
            description="Consumer must negotiate contract before accessing data",
            license="CC-BY-4.0",
            purpose="Research and analytics",
            constraints=["No redistribution", "Attribution required"],
        )

    offering_id = f"offering-{DATASET_ID}-{uuid.uuid4().hex[:8]}"

    offering = DataOffering(
        offeringId=offering_id,
        datasetId=DATASET_ID,
        title=metadata.get("title", metadata.get("dct:title", "Building Energy Consumption Dataset API")),
        description=metadata.get("description", metadata.get("dct:description", "")),
        providerName=PROVIDER_NAME,
        endpointUrl="http://localhost:8000/api/energy/buildings/hourly",
        format=metadata.get("format", "application/json"),
        frequency=metadata.get("frequency", "hourly"),
        unit=metadata.get("unit", "kWh"),
        spatialCoverage=metadata.get("spatial", metadata.get("spatialCoverage", "Shenzhen demo district")),
        temporalStart=metadata.get("temporalStart", "2026-05-01"),
        temporalEnd=metadata.get("temporalEnd", "2026-05-02"),
        policy=policy,
        metadata=metadata,
        contractTemplate=openapi_spec,
        createdAt=datetime.now(timezone.utc).isoformat(),
        status="ACTIVE",
    )

    offerings[offering_id] = offering
    log.info("Offering created: id=%s title=%s", offering_id, offering.title)
    return offering


# ============================================================
# Data Discovery - Catalog
# ============================================================


@app.get("/api/catalog")
async def get_catalog():
    """Data Catalog - 列出所有已发布的 offerings。"""
    if not offerings:
        return {
            "catalog": [],
            "total": 0,
            "provider": PROVIDER_NAME,
            "hint": "No offerings published yet. POST /api/catalog/offerings to create one.",
        }

    catalog_items = []
    for o in offerings.values():
        catalog_items.append({
            "offeringId": o.offeringId,
            "datasetId": o.datasetId,
            "title": o.title,
            "providerName": o.providerName,
            "endpointUrl": o.endpointUrl,
            "policy": o.policy.model_dump(),
            "status": o.status,
        })

    return {
        "catalog": catalog_items,
        "total": len(catalog_items),
        "provider": PROVIDER_NAME,
    }


@app.get("/api/catalog/{offering_id}")
async def get_offering(offering_id: str):
    """查看单个 offering 详情，含 metadata (JSON-LD) + contract template (OpenAPI)。"""
    offering = offerings.get(offering_id)
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    return offering


# ============================================================
# Contract Negotiation - State Machine
# ============================================================
#
#  REQUESTED  ──→  CONFIRMED  ──→  AGREED
#       │              │
#       └──→  DECLINED  └──→  ERROR
#


@app.post("/api/contract-negotiations", response_model=ContractNegotiation)
async def start_negotiation(request: ContractNegotiationRequest):
    """
    Consumer 发起合同协商。
    Provider 自动确认并生成 contractId，状态流转：REQUESTED → CONFIRMED → AGREED
    """
    offering = offerings.get(request.offeringId)
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")

    if offering.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Offering is not active")

    negotiation_id = f"neg-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    negotiation = ContractNegotiation(
        negotiationId=negotiation_id,
        offeringId=request.offeringId,
        consumerDID=request.consumerDID,
        providerDID=request.providerDID or PROVIDER_DID,
        state=NegotiationState.REQUESTED,
        createdAt=now,
        updatedAt=now,
        stateHistory=[{"state": "REQUESTED", "timestamp": now, "detail": "Consumer initiated negotiation"}],
    )

    negotiations[negotiation_id] = negotiation
    log.info("Negotiation started: id=%s offering=%s consumer=%s", negotiation_id, request.offeringId, request.consumerDID)

    # Auto-advance: REQUESTED → CONFIRMED (Provider acknowledges)
    now2 = datetime.now(timezone.utc).isoformat()
    negotiation.state = NegotiationState.CONFIRMED
    negotiation.updatedAt = now2
    negotiation.stateHistory.append({"state": "CONFIRMED", "timestamp": now2, "detail": "Provider confirmed negotiation"})

    # Auto-advance: CONFIRMED → AGREED (Contract created)
    contract_id = f"contract-{uuid.uuid4().hex[:8]}"
    now3 = datetime.now(timezone.utc).isoformat()
    negotiation.state = NegotiationState.AGREED
    negotiation.contractId = contract_id
    negotiation.updatedAt = now3
    negotiation.stateHistory.append({"state": "AGREED", "timestamp": now3, "detail": f"Contract {contract_id} created"})

    return negotiation


@app.get("/api/contract-negotiations/{negotiation_id}", response_model=ContractNegotiation)
async def get_negotiation(negotiation_id: str):
    """查询合同协商状态。"""
    negotiation = negotiations.get(negotiation_id)
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return negotiation


@app.get("/api/contract-negotiations")
async def list_negotiations():
    """列出所有合同协商。"""
    return {
        "negotiations": [n.model_dump() for n in negotiations.values()],
        "total": len(negotiations),
    }


# ============================================================
# Transfer Process - State Machine
# ============================================================
#
#  REQUESTED  ──→  STARTED  ──→  COMPLETED
#       │              │
#       └──→ TERMINATED └──→  SUSPENDED
#


@app.post("/api/transfer-processes", response_model=TransferProcess)
async def start_transfer(request: TransferProcessRequest):
    """
    Consumer 发起数据传输。
    必须先有 AGREED 状态的 negotiation。
    状态流转：REQUESTED → STARTED → COMPLETED
    """
    negotiation = negotiations.get(request.negotiationId)
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    if negotiation.state != NegotiationState.AGREED:
        raise HTTPException(
            status_code=400,
            detail=f"Negotiation must be AGREED to start transfer. Current state: {negotiation.state}",
        )

    offering = offerings.get(negotiation.offeringId)
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")

    transfer_id = f"transfer-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    transfer = TransferProcess(
        transferId=transfer_id,
        negotiationId=request.negotiationId,
        offeringId=negotiation.offeringId,
        state=TransferState.REQUESTED,
        dataAddress=request.dataAddress,
        resourceAddress={
            "type": "HttpData",
            "baseUrl": offering.endpointUrl,
            "authKey": "Authorization",
            "authCode": "",  # Would be filled with real token
        },
        createdAt=now,
        updatedAt=now,
        stateHistory=[{"state": "REQUESTED", "timestamp": now, "detail": "Consumer initiated transfer"}],
    )

    transfers[transfer_id] = transfer
    log.info("Transfer started: id=%s negotiation=%s", transfer_id, request.negotiationId)

    # Auto-advance: REQUESTED → STARTED
    now2 = datetime.now(timezone.utc).isoformat()
    transfer.state = TransferState.STARTED
    transfer.updatedAt = now2
    transfer.stateHistory.append({"state": "STARTED", "timestamp": now2, "detail": "Provider started data provisioning"})

    # Auto-advance: STARTED → COMPLETED
    now3 = datetime.now(timezone.utc).isoformat()
    transfer.state = TransferState.COMPLETED
    transfer.updatedAt = now3
    transfer.stateHistory.append({"state": "COMPLETED", "timestamp": now3, "detail": "Data is ready for retrieval"})

    return transfer


@app.get("/api/transfer-processes/{transfer_id}", response_model=TransferProcess)
async def get_transfer(transfer_id: str):
    """查询传输过程状态。"""
    transfer = transfers.get(transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return transfer


@app.get("/api/transfer-processes")
async def list_transfers():
    """列出所有传输过程。"""
    return {
        "transfers": [t.model_dump() for t in transfers.values()],
        "total": len(transfers),
    }


# ============================================================
# Data Endpoints (unchanged)
# ============================================================


@app.get("/api/energy/buildings/hourly", response_model=EnergyDataset)
async def get_energy_data(
    buildingId: Optional[str] = Query(None, description="Filter by building ID"),
    from_date: Optional[str] = Query(None, alias="from", description="Start time (ISO format)"),
    to_date: Optional[str] = Query(None, alias="to", description="End time (ISO format)"),
    authorization: Optional[str] = Header(None),
):
    """Hourly energy consumption data endpoint. Requires valid JWT token."""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization required. POST /auth/token to get access token.",
        )

    payload = verify_token(authorization)

    data = load_sample_data()
    records = data.get("records", [])

    if buildingId:
        records = [r for r in records if r["buildingId"] == buildingId]
    if from_date:
        records = [r for r in records if r["timestamp"] >= from_date]
    if to_date:
        records = [r for r in records if r["timestamp"] <= to_date]

    log.info("Data requested: records=%d buildingId=%s", len(records), buildingId or "all")

    return EnergyDataset(
        datasetId=data["datasetId"],
        providerName=data["providerName"],
        license=data["license"],
        records=[EnergyReading(**r) for r in records],
    )


# ============================================================
# Metadata Endpoints
# ============================================================


@app.get("/api/metadata")
async def get_metadata():
    """Data product metadata in JSON-LD format."""
    return load_metadata()


# ============================================================
# Health & Info Endpoints
# ============================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "provider": PROVIDER_NAME,
        "dataset": DATASET_ID,
        "scenario": DEFAULT_SCENARIO,
        "dataFile": str(scenario_data_dir() / DEFAULT_DATA_FILE),
        "metadataFile": str(scenario_metadata_dir() / DEFAULT_METADATA_FILE),
        "contractFile": str(scenario_mock_api_dir() / DEFAULT_OPENAPI_FILE),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root():
    """API root with available endpoints."""
    return {
        "service": "Building Energy Consumption Dataset API",
        "provider": PROVIDER_NAME,
        "version": "0.2.0",
        "endpoints": {
            "publish": "POST /api/catalog/offerings",
            "catalog": "GET /api/catalog",
            "offering_detail": "GET /api/catalog/{offeringId}",
            "negotiate": "POST /api/contract-negotiations",
            "negotiation_status": "GET /api/contract-negotiations/{negotiationId}",
            "transfer": "POST /api/transfer-processes",
            "transfer_status": "GET /api/transfer-processes/{transferId}",
            "data": "GET /api/energy/buildings/hourly",
            "metadata": "GET /api/metadata",
            "auth": "POST /auth/token",
            "health": "GET /health",
        },
        "demo_credentials": {
            "client_id": "city-analytics-lab",
            "note": "Demo credentials are defined in config.py; the secret is intentionally omitted here.",
        },
    }


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
