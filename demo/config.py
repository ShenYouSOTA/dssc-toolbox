"""
FIWARE DSC Demo - 集中配置

所有 Demo 共享的配置项，避免硬编码散落。
"""

import logging
import os
from pathlib import Path

# ============================================================
# 路径
# ============================================================

DEMO_DIR = Path(__file__).parent

# ============================================================
# Scenario data layout
# ============================================================
# Demo data lives under demo/data/scenarios/<scenario-name>/ so that
# the Python demo is self-contained and can be extended with new
# scenarios or swapped for real data sources without leaving the demo
# directory.
#
# Expected structure per scenario:
#   data/              - payload files (e.g. building-energy-sample.json)
#   metadata/          - JSON-LD metadata files
#   mock-api/          - OpenAPI contract templates
#   shapes/            - SHACL shapes (optional, for validation demos)
#   gaia-x/            - Gaia-X credential templates (optional)

SCENARIOS_DIR = DEMO_DIR / "data" / "scenarios"
DEFAULT_SCENARIO = os.environ.get("DEMO_SCENARIO", "DSSC_Minimal_Energy_Scenario")


def scenario_dir(name: str | None = None) -> Path:
    """Return the base directory for a named scenario."""
    return SCENARIOS_DIR / (name or DEFAULT_SCENARIO)


def scenario_data_dir(name: str | None = None) -> Path:
    """Return the data payload directory for a named scenario."""
    return scenario_dir(name) / "data"


def scenario_metadata_dir(name: str | None = None) -> Path:
    """Return the metadata directory for a named scenario."""
    return scenario_dir(name) / "metadata"


def scenario_mock_api_dir(name: str | None = None) -> Path:
    """Return the mock-api contract directory for a named scenario."""
    return scenario_dir(name) / "mock-api"


# Backwards-compatible aliases for the default scenario
SCENARIO_DIR = scenario_dir()
DATA_DIR = scenario_data_dir()
METADATA_DIR = scenario_metadata_dir()
OPENAPI_DIR = scenario_mock_api_dir()
LOG_DIR = DEMO_DIR / "logs"

# Default asset file names within a scenario. These can be overridden by
# environment variables to switch to a different payload or contract
# without changing code.
DEFAULT_DATA_FILE = os.environ.get("DEMO_DATA_FILE", "building-energy-sample.json")
DEFAULT_METADATA_FILE = os.environ.get("DEMO_METADATA_FILE", "data-product-valid.jsonld")
DEFAULT_OPENAPI_FILE = os.environ.get("DEMO_OPENAPI_FILE", "openapi.yaml")

# ============================================================
# Provider 配置
# ============================================================

PROVIDER_NAME = "Energy Data Provider Ltd."
DATASET_ID = "building-energy-hourly-v1"
PROVIDER_DID = "did:web:energy-provider.example.org"

# 最终公网 DID (did.json 发布到 GitHub Pages, 私钥见 demo/data/keys/, demo 专用)
# 未定稿前默认为集群内 DID; 定稿后改为路径型 did:web:<org>.github.io:<repo> 或自有域名
PROVIDER_PUBLIC_DID = os.environ.get("DSSC_PROVIDER_DID", "did:web:shenyousota.github.io:dssc-toolbox")

# ============================================================
# JWT / Auth
# ============================================================

# WARNING: The default JWT secret below is for local demo only. Always set
# DEMO_JWT_SECRET to a strong random value in production or shared environments.
JWT_SECRET = os.environ.get("DEMO_JWT_SECRET", "dssc-demo-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("DEMO_JWT_EXPIRY_HOURS", "2"))

# Demo 客户端凭证
DEMO_CLIENTS = {
    "city-analytics-lab": {
        "secret": "consumer-secret-123",
        "role": "consumer",
        "name": "City Analytics Lab",
        "did": "did:web:city-analytics-lab.example.org",
    }
}

DEFAULT_CLIENT_ID = "city-analytics-lab"
DEFAULT_CLIENT_SECRET = "consumer-secret-123"
CONSUMER_DID = "did:web:city-analytics-lab.example.org"

# ============================================================
# Mock Server
# ============================================================

MOCK_HOST = os.environ.get("DEMO_MOCK_HOST", "0.0.0.0")
MOCK_PORT = int(os.environ.get("DEMO_MOCK_PORT", "8000"))

# ============================================================
# Real Cluster (port-forward 端口映射)
# ============================================================

KUBECONFIG = os.environ.get("KUBECONFIG", "/tmp/k3s.yaml")

CLUSTER_PORTS = {
    "provider-keycloak": 8443,
    "consumer-keycloak": 8444,
    "provider-verifier": 8445,
    "provider-scorpio": 8446,
    "provider-tmf-api": 8447,
    "provider-til": 8448,
    "provider-dashboard": 8449,
    "provider-marketplace": 8450,
    "ta-tir": 8451,
}

# Keycloak 配置 (真实集群)
KC_REALM = os.environ.get("DEMO_KC_REALM", "test-realm")
KC_CLIENT_ID = os.environ.get("DEMO_KC_CLIENT_ID", "account-console")
KC_USERNAME = os.environ.get("DEMO_KC_USERNAME", "employee")
KC_PASSWORD = os.environ.get("DEMO_KC_PASSWORD", "test")

# ============================================================
# Logging
# ============================================================


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """统一日志配置"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
