"""
DID identity 工具 - 生成/管理 Provider 的固定 demo 密钥对与 did.json

用途：
  1. keygen      生成一次性 P-256 密钥对（私钥提交进仓库，demo 专用）
  2. did         由公钥确定性生成 did.json（发布到 GitHub Pages 供公网解析）
  3. k8s-secret  输出把同一密钥导入 k3s 集群的命令（替代 cert-manager 随机签发）
  4. verify      拉取公网 did.json，校验其与本地私钥匹配
  5. cert        生成 demo CA + 叶子证书链（供 did --x5c 嵌入 did.json）

安全说明：
  私钥提交进仓库仅限本教学 demo（虚构主体 Energy Data Provider Ltd.）。
  生产环境严禁提交私钥。

x5c 说明（方案 B，Gaia-X Compliance L3 信任锚试探）：
  demo CA 为自签 CA，不在任何公开 trust store 中，大概率仍无法通过
  Gaia-X 认可 CA 锚定校验；嵌入 x5c 的目的是验证 Compliance Service 的
  格式层接受度，并在 demo 层面提供完整证书链证据。密钥材料不变，
  嵌入 x5c 后已签发的 VC/VP-JWT 无需重签。

用法：
  uv run python did_identity.py keygen
  uv run python did_identity.py cert
  uv run python did_identity.py did --did did:web:shenyousota.github.io:dssc-toolbox --x5c
  uv run python did_identity.py k8s-secret
  uv run python did_identity.py verify --did did:web:shenyousota.github.io:dssc-toolbox
"""

import argparse
import base64
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

DEMO_DIR = Path(__file__).parent
REPO_ROOT = DEMO_DIR.parent
KEYS_DIR = DEMO_DIR / "data" / "keys"

PRIVATE_JWK_FILE = KEYS_DIR / "provider-key.private.jwk.json"
PUBLIC_JWK_FILE = KEYS_DIR / "provider-key.public.jwk.json"
TLS_KEY_FILE = KEYS_DIR / "tls.key"
TLS_CRT_FILE = KEYS_DIR / "tls.crt"
CA_KEY_FILE = KEYS_DIR / "demo-ca.key"
CA_CRT_FILE = KEYS_DIR / "demo-ca.crt"
LEAF_CRT_FILE = KEYS_DIR / "provider-leaf.crt"

DEFAULT_DID = "did:web:shenyousota.github.io:dssc-toolbox"
KEY_ID_SUFFIX = "key-1"

DEMO_KEY_WARNING = "DEMO KEY - NOT FOR PRODUCTION. 虚构主体 Energy Data Provider Ltd. 教学演示专用。"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _int_to_b64url(value: int, length: int = 32) -> str:
    return _b64url(value.to_bytes(length, "big"))


def private_key_to_jwk(key: ec.EllipticCurvePrivateKey) -> dict:
    numbers = key.private_numbers()
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": _int_to_b64url(numbers.public_numbers.x),
        "y": _int_to_b64url(numbers.public_numbers.y),
        "d": _int_to_b64url(numbers.private_value),
    }


def public_key_to_jwk(key: ec.EllipticCurvePublicKey) -> dict:
    numbers = key.public_numbers()
    return {
        "kty": "EC",
        "crv": "P-256",
        "alg": "ES256",
        "x": _int_to_b64url(numbers.x),
        "y": _int_to_b64url(numbers.y),
    }


def load_private_key() -> ec.EllipticCurvePrivateKey:
    if not TLS_KEY_FILE.exists():
        sys.exit(f"私钥不存在: {TLS_KEY_FILE}\n先运行: uv run python did_identity.py keygen")
    with open(TLS_KEY_FILE, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
        sys.exit("私钥不是 P-256 EC 密钥，请重新 keygen")
    return key


def did_web_to_url(did: str) -> str:
    """did:web 规范：did:web:host -> https://host/.well-known/did.json
    did:web:host:path:sub -> https://host/path/sub/did.json（注意：带路径时没有 .well-known）"""
    if not did.startswith("did:web:"):
        sys.exit(f"仅支持 did:web，收到: {did}")
    parts = did[len("did:web:"):].split(":")
    host = unquote(parts[0])
    if len(parts) == 1:
        return f"https://{host}/.well-known/did.json"
    path = "/".join(unquote(p) for p in parts[1:])
    return f"https://{host}/{path}/did.json"


def did_web_to_repo_path(did: str) -> Path:
    """did.json 在本仓库中的落盘位置（GitHub Pages deploy-from-branch 从仓库根服务）。

    GitHub Pages project site 规则：<org>.github.io/<repo>/<rest> 中第一段是仓库名，
    映射到本仓库根目录，因此落盘时去掉第一段。
    其他静态托管（自有域名）按 URL 路径原样落盘。"""
    parts = did[len("did:web:"):].split(":")
    host = unquote(parts[0])
    url = did_web_to_url(did)
    rel = url[len("https://"):].split("/", 1)[1] if "/" in url[len("https://"):] else ".well-known/did.json"
    if host.endswith(".github.io") and "/" in rel:
        rel = rel.split("/", 1)[1]
    return REPO_ROOT / rel


def cmd_keygen(args: argparse.Namespace) -> None:
    if PRIVATE_JWK_FILE.exists() and not args.force:
        sys.exit(f"密钥已存在: {PRIVATE_JWK_FILE}\n如需重新生成（会使已签发凭证全部失效）: --force")

    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())

    # PKCS8 PEM 私钥（k8s tls.key 用）
    TLS_KEY_FILE.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )

    # 自签名证书（k8s tls.crt / ca.crt 用；集群内 TLS 本来就是自签名 CA 体系）
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Energy Data Provider Ltd. (DEMO)")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    TLS_CRT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    private_jwk = {"_comment": DEMO_KEY_WARNING, **private_key_to_jwk(key)}
    public_jwk = public_key_to_jwk(key.public_key())
    PRIVATE_JWK_FILE.write_text(json.dumps(private_jwk, indent=2) + "\n")
    PUBLIC_JWK_FILE.write_text(json.dumps(public_jwk, indent=2) + "\n")

    print(f"已生成 P-256 密钥对（{DEMO_KEY_WARNING}）:")
    print(f"  私钥 JWK : {PRIVATE_JWK_FILE.relative_to(REPO_ROOT)}")
    print(f"  公钥 JWK : {PUBLIC_JWK_FILE.relative_to(REPO_ROOT)}")
    print(f"  tls.key  : {TLS_KEY_FILE.relative_to(REPO_ROOT)}")
    print(f"  tls.crt  : {TLS_CRT_FILE.relative_to(REPO_ROOT)}")
    print()
    print("下一步: uv run python did_identity.py did --did <最终DID>")


def cmd_cert(args: argparse.Namespace) -> None:
    if CA_CRT_FILE.exists() and not args.force:
        sys.exit(f"证书链已存在: {CA_CRT_FILE}\n如需重新生成（会使已嵌入的 x5c 失效）: --force")

    provider_key = load_private_key()
    ca_key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)

    ca_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "DSSC Demo CA (DEMO)"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "City Energy Data Space Authority (DEMO)"),
    ])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    leaf_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Energy Data Provider Ltd. (DEMO)"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Energy Data Provider Ltd. (DEMO)"),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
    ])
    leaf_cert = (
        x509.CertificateBuilder()
        .subject_name(leaf_name)
        .issuer_name(ca_name)
        .public_key(provider_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(args.did)]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    CA_KEY_FILE.write_bytes(
        ca_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    CA_CRT_FILE.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    LEAF_CRT_FILE.write_bytes(leaf_cert.public_bytes(serialization.Encoding.PEM))

    print(f"已生成 demo 证书链（{DEMO_KEY_WARNING}）:")
    print(f"  CA 私钥  : {CA_KEY_FILE.relative_to(REPO_ROOT)}")
    print(f"  CA 证书  : {CA_CRT_FILE.relative_to(REPO_ROOT)}")
    print(f"  叶子证书 : {LEAF_CRT_FILE.relative_to(REPO_ROOT)}（绑定 provider 公钥，SAN={args.did}）")
    print()
    print("下一步: uv run python did_identity.py did --did <最终DID> --x5c")


def load_x5c() -> list:
    """读取证书链并输出 JWK x5c 格式（base64 标准编码 DER，叶子在前，无 PEM 头）。"""
    if not LEAF_CRT_FILE.exists() or not CA_CRT_FILE.exists():
        sys.exit(f"证书链不存在，先运行: uv run python did_identity.py cert")
    chain = []
    for path in (LEAF_CRT_FILE, CA_CRT_FILE):
        cert = x509.load_pem_x509_certificate(path.read_bytes())
        chain.append(base64.standard_b64encode(cert.public_bytes(serialization.Encoding.DER)).decode("ascii"))
    return chain


def build_did_document(did: str, public_jwk: dict) -> dict:
    kid = f"{did}#{KEY_ID_SUFFIX}"
    return {
        "@context": ["https://www.w3.org/ns/did/v1"],
        "id": did,
        "verificationMethod": [
            {
                "id": kid,
                "type": "JsonWebKey2020",
                "controller": did,
                "publicKeyJwk": public_jwk,
            }
        ],
        "authentication": [kid],
        "assertionMethod": [kid],
    }


def cmd_did(args: argparse.Namespace) -> None:
    did = args.did
    key = load_private_key()
    public_jwk = public_key_to_jwk(key.public_key())
    if args.x5c:
        public_jwk["x5c"] = load_x5c()

    doc = build_did_document(did, public_jwk)
    out_path = did_web_to_repo_path(did)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2) + "\n")

    print(f"DID        : {did}")
    print(f"解析 URL   : {did_web_to_url(did)}")
    print(f"已写入     : {out_path.relative_to(REPO_ROOT)}")
    print()
    print("发布步骤（GitHub Pages，零成本）:")
    print("  1. git add 上述 did.json 并 push")
    print("  2. 仓库 Settings -> Pages -> Source: Deploy from a branch -> 当前默认分支 / (root)")
    print(f"  3. 验证: curl {did_web_to_url(did)}")


def cmd_k8s_secret(args: argparse.Namespace) -> None:
    load_private_key()  # 确认密钥存在
    print("将仓库固定密钥导入 k3s（替代 cert-manager 随机签发的 mp-operations.org-tls）:")
    print()
    print(f"kubectl --kubeconfig=/tmp/k3s.yaml delete secret mp-operations.org-tls -n provider 2>/dev/null")
    print(
        "kubectl --kubeconfig=/tmp/k3s.yaml create secret tls mp-operations.org-tls "
        f"--cert={TLS_CRT_FILE} --key={TLS_KEY_FILE} -n provider"
    )
    print()
    print("注意: 集群 did helper 的 hostUrl 和 did.json 里的 DID 必须一致，")
    print("      若 DID 改为公网版，provider.yaml 中 did.config.server.hostUrl 同步修改。")


def cmd_verify(args: argparse.Namespace) -> None:
    did = args.did
    url = did_web_to_url(did)
    key = load_private_key()
    expected = public_key_to_jwk(key.public_key())

    print(f"拉取 {url} ...")
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        sys.exit(f"拉取失败: {e}")

    doc = resp.json()
    methods = doc.get("verificationMethod", [])
    if not methods:
        sys.exit("did.json 中没有 verificationMethod")
    remote_jwk = methods[0].get("publicKeyJwk", {})
    remote = {k: remote_jwk.get(k) for k in ("kty", "crv", "x", "y")}

    if remote == expected:
        print(f"公钥匹配，DID {did} 公网解析正常")
        print(f"  kid: {methods[0].get('id')}")
    else:
        print("公钥不匹配！公网 did.json 与本地私钥不是同一把密钥:")
        print(f"  本地 : {expected}")
        print(f"  远端 : {remote}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("keygen", help="生成 P-256 密钥对（一次性）")
    p.add_argument("--force", action="store_true", help="覆盖已有密钥")
    p.set_defaults(func=cmd_keygen)

    p = sub.add_parser("did", help="由公钥生成 did.json")
    p.add_argument("--did", default=DEFAULT_DID, help=f"最终公网 DID（默认 {DEFAULT_DID}）")
    p.add_argument("--x5c", action="store_true", help="在 JWK 中嵌入 demo 证书链（先运行 cert）")
    p.set_defaults(func=cmd_did)

    p = sub.add_parser("cert", help="生成 demo CA + 叶子证书链（供 --x5c 使用）")
    p.add_argument("--did", default=DEFAULT_DID, help="写入叶子证书 SAN 的 DID")
    p.add_argument("--force", action="store_true", help="覆盖已有证书链")
    p.set_defaults(func=cmd_cert)

    p = sub.add_parser("k8s-secret", help="输出导入 k3s 的命令")
    p.set_defaults(func=cmd_k8s_secret)

    p = sub.add_parser("verify", help="校验公网 did.json 与本地私钥匹配")
    p.add_argument("--did", default=DEFAULT_DID)
    p.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
