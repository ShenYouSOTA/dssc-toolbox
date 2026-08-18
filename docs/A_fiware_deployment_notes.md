# FIWARE DSC 部署笔记

本文档记录 FIWARE Data Space Connector (DSC) 在 k3s 本地环境中的完整部署过程，包括踩坑记录、技术选型分析和配置参考。

---

## 1. 环境与前置条件

### 硬件要求

| 资源 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 内存 | 16 GB | ≥ 24 GB |
| CPU | 4 核 | 8 核 |
| 磁盘 | 10 GB | SSD 优先 |
| 操作系统 | Linux / macOS | Ubuntu |

### 必需工具

| 工具 | 版本 | 用途 |
|------|------|------|
| Docker | 27.0+ | 运行 k3s 容器 |
| kubectl | latest | Kubernetes 管理 |
| helm | 3.x | Chart 部署 |
| Python | 3.10+ | Demo 运行 |
| uv | latest | Python 包管理 |

### k3s 集群启动

```bash
# 启动 k3s (Docker 方式, 禁用 traefik)
docker run -d --name k3s-server \
    --privileged \
    -p 6443:6443 \
    -p 80:80 \
    -p 443:443 \
    -v k3s-data:/var/lib/rancher/k3s \
    rancher/k3s:latest server \
    --disable=traefik

# 获取 kubeconfig
docker exec k3s-server cat /etc/rancher/k3s/k3s.yaml > /tmp/k3s.yaml
export KUBECONFIG=/tmp/k3s.yaml
```

> **容器已存在时的重启：** `just up` / 上述 `docker run` 会因同名容器报 `Conflict`。
> 直接复用已有容器即可（数据在 `k3s-data` volume 中持久化）：
> ```bash
> docker start k3s-server
> docker exec k3s-server cat /etc/rancher/k3s/k3s.yaml > /tmp/k3s.yaml   # 必须刷新，旧证书/IP 会失效
> ```

---

## macOS 环境差异

在 macOS 上运行本节 k3s 部署时，需额外注意以下差异。

### Docker Desktop 配置

- **Settings → General → Use virtualization framework**: 建议选择 Apple Virtualization framework。
- **Settings → Resources**: CPU 建议 ≥ 4，内存建议 ≥ 16 GB；若部署 Provider + Consumer 双角色，推荐 24 GB 以上。
- **Settings → General → Rosetta**: 开启 x86/AMD64 模拟，以运行官方 `linux/amd64` 容器镜像。

### 与 Linux 部署的差异

- Docker Desktop 在 macOS 上有一层额外虚拟化网络，端口 80/443 被系统占用概率较低，但 `host.docker.internal` 等网络行为可能与 Linux 不同。
- 国内网络环境下，Docker Hub（`stoplight/prism`、`docker.io/fiware/*` 等）与 quay.io 官方镜像可能触发 `TLS handshake timeout` 或 `context deadline exceeded`。建议配置镜像加速器、镜像代理，或预先通过 `docker pull` + `docker save` / `docker load` 导入关键镜像。
- Apple Silicon 芯片通过 Rosetta 2 模拟运行重型 Java 容器（Keycloak、Scorpio、TMForum API 等）时，可能出现启动慢、内存高或偶发网络中断。如频繁失败，可考虑 `demo/README.md` 中介绍的轻量白盒 Connector 方案。

### 常用命令对照

macOS 下除 Docker Desktop 自身操作外，其余命令与 Linux 基本一致：

| 操作 | Linux | macOS |
|---|---|---|
| 查看端口占用 | `lsof -i :8000` | `lsof -i :8000`（相同） |
| 杀掉端口进程 | `kill -9 <PID>` | `kill -9 <PID>`（相同） |
| 启动 k3s | Docker 容器 | Docker Desktop 虚拟机内运行 |

## Windows + WSL2 Ubuntu 部署

Windows 环境下完整部署 FIWARE DSC 的推荐路径是 Docker Desktop + WSL2 Ubuntu + k3s。

### 环境栈

- 宿主机：Windows 10/11 + Docker Desktop（启用 WSL2 backend）
- 子系统：WSL2 Ubuntu
- 编排：k3s 运行在 WSL2 中
- 访问方式：`*.127.0.0.1.nip.io:8443`

### 与 Linux 部署的差异

| 项目 | Linux（原生/Docker） | Windows + WSL2 |
|---|---|---|
| Docker 运行方式 | 原生 Docker 引擎或 Docker 容器 | Docker Desktop → WSL2 后端 |
| k3s 运行位置 | 本机或 Docker 容器 | WSL2 Ubuntu 内部 |
| 服务入口 | `*.127.0.0.1.nip.io`（默认 443） | `*.127.0.0.1.nip.io:8443` |
| 本地数据路径 | 相对路径或容器内 | `~/DSSC_projects/...`（WSL2 文件系统） |

### 完整流程

该分支提供从 Provider 创建本地数据、上传到 Scorpio、发布 Product Offering，到 Consumer 通过 OID4VP 获取 Access Token 并下载受保护数据的完整流程。切换到 GitHub 分支查看详细步骤与脚本：

```text
https://github.com/ShenYouSOTA/DSSC-Toolbox/tree/feature/ytt-full-data-space-demo
```

## 2. 技术选型

### 2.1 官方约束（FDSC Helm Chart 强制要求）

以下组件由 FIWARE DSC 的 Helm Umbrella Chart 定义，部署时无法绕过：

| 组件 | 作用 | 说明 |
|------|------|------|
| **Keycloak** | OIDC Provider / 凭证签发 | CloudPirates 维护的 patched 版本 (26.6.2) |
| **MongoDB** | Scorpio Context Broker 后端 | NGSI-LD 实体存储 |
| **PostgreSQL** | TMForum / Keycloak / Verifier 后端 | 关系型数据存储 |
| **cert-manager** | TLS 证书自动签发 | 所有 Ingress 的 HTTPS 依赖 |
| **APISIX** | API Gateway / PEP | 策略执行点，与 OPA 联动 |
| **OPA** | 策略决策点 (PDP) | 执行 ODRL 策略 |
| **ODRL-PAP** | 策略管理点 | ODRL 策略存储与加载 |
| **VCVerifier** | 凭证验证 | OID4VP 认证端点 |
| **DID Helper** | 去中心化身份 | `did:web` 文档服务 |
| **TMForum API** | 产品目录管理 | ProductSpecification / ProductOffering |
| **Scorpio** | NGSI-LD Context Broker | 数据服务 (Quarkus/Java) |

**数据模型约束：**
- 数据必须以 NGSI-LD 格式存储到 Scorpio
- 产品目录必须通过 TMForum Open API 管理
- 认证必须走 OID4VP / Verifiable Credentials 流程
- DID 必须注册到 Trusted Issuers Registry (TIR)

### 2.2 自选方案（本项目选择）

以下选择是本项目为本地开发演示而做的决策，非 FDSC 官方要求：

| 决策点 | 选择 | 理由 | 替代方案 |
|--------|------|------|---------|
| **容器编排** | k3s (Docker 容器) | 轻量、启动快、资源占用少 | minikube, kind, 裸机 k8s |
| **Ingress Controller** | nginx-ingress | 社区成熟、配置灵活 | traefik (k3s 默认) |
| **k3s 启动参数** | `--disable=traefik` | 避免与 nginx-ingress 端口冲突 | 不禁用，只装一个 |
| **域名解析** | nip.io (`*.127.0.0.1.nip.io`) | 无需修改 /etc/hosts，自动解析到 127.0.0.1 | CoreDNS 配置, /etc/hosts |
| **PostgreSQL Operator** | Zalando postgres-operator | FDSC Chart 内置支持 | CloudNativePG |
| **Demo 语言** | Python (FastAPI + httpx) | 开发速度快、依赖轻量 | Java (官方 SDK), Go |
| **包管理** | uv | 极速依赖解析 | pip, poetry |
| **自动化** | justfile | 语义清晰、易维护 | Makefile, shell 脚本 |
| **配置管理** | config.py 集中配置 | 类型安全、IDE 补全 | .env 文件, YAML |

### 2.3 命名空间划分

```
trust-anchor/     → TIR (Trusted Issuers Registry)
provider/         → Keycloak, Verifier, MongoDB, PostgreSQL, Scorpio, TMForum, APISIX, Dashboard
consumer/         → Keycloak, PostgreSQL
ingress-nginx/    → nginx-ingress-controller
cert-manager/     → cert-manager
postgres-operator/→ Zalando PostgreSQL Operator
```

---

## 3. 部署流程（按依赖顺序）

```bash
# 一键启动全部
just up

# 或手动分步：
just k3s-start && just k3s-wait
just deploy-infra        # cert-manager + postgres-operator
just deploy-apps         # trust-anchor + provider + consumer
just smoke-test
```

### 3.1 基础设施层（必须先于应用部署）

```bash
# 1. cert-manager (TLS 证书签发)
helm install cert-manager jetstack/cert-manager \
    --namespace cert-manager --create-namespace \
    --set crds.enabled=true --wait --timeout 5m

# 2. Zalando PostgreSQL Operator (数据库管理)
helm install postgres-operator postgres-operator/postgres-operator \
    --namespace postgres-operator --create-namespace \
    --wait --timeout 5m
```

### 3.2 应用层

```bash
# 3. Trust Anchor (TIR)
helm install trust-anchor charts/trust-anchor \
    -f k3s/trust-anchor.yaml \
    --namespace trust-anchor --create-namespace --wait --timeout 5m

# 4. Provider (完整数据空间提供者)
helm install provider charts/data-space-connector \
    -f k3s/provider.yaml \
    --namespace provider --create-namespace --wait --timeout 10m

# 5. Consumer (消费者角色)
kubectl create secret generic keystore-password \
    --from-literal=password=changeit -n consumer
helm install consumer charts/data-space-connector \
    -f k3s/consumer.yaml \
    --namespace consumer --create-namespace --wait --timeout 10m \
    --set decentralizedIam.vcAuthentication.postgres-operator.enabled=false
```

### 3.3 Ingress 配置

```bash
# 6. nginx-ingress-controller
helm install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx --create-namespace

# 7. 为所有 Ingress 添加 ingressClassName
kubectl get ingress -A -o name | xargs -I {} kubectl patch {} \
    --type merge -p '{"spec":{"ingressClassName":"nginx"}}'
```

---

## 4. 踩坑记录

### 4.1 镜像拉取超时

**现象：** MongoDB Pod 处于 `ImagePullBackOff` 状态，`quay.xuanyuan.me` 镜像拉取超时。

**根因：** `quay.xuanyuan.me` 是国内镜像代理，网络不稳定时会超时。`docker.io/fiware/biz-ecosystem-charging-backend:11.3.1` 同样受限于 Docker Hub 速率限制。

**解决方案：**
- 等待网络恢复后重试
- 使用其他镜像代理（如 `docker.1ms.run`）
- 预先 `docker pull` 镜像后导入 k3s 容器

**验证命令：**
```bash
kubectl get pods -n provider | grep -E "ImagePull|ErrImage"
```

---

### 4.2 CRD 缺失

**现象：** Provider 部署时 Pod 卡在 `Pending`，事件显示 `persistentvolumeclaim not found` 或 `CRD not found`。

**根因：** FDSC Chart 依赖 Zalando PostgreSQL Operator 的 CRD（如 `postgresql`）和 MongoDB Operator 的 CRD。这些 Operator 未预装。

**解决方案：**
```bash
# 安装 Zalando PostgreSQL Operator
helm install postgres-operator postgres-operator/postgres-operator \
    --namespace postgres-operator --create-namespace

# MongoDB: 使用 managedMongo (Chart 内置 StatefulSet) 而非 Operator
# 在 provider.yaml 中设置:
# mongo-operator:
#   enabled: false
# managedMongo:
#   enabled: true
```

**验证命令：**
```bash
kubectl get crd | grep -E "postgresql|mongodb"
kubectl get pods -n postgres-operator
```

---

### 4.3 cert-manager 未安装

**现象：** Ingress 的 TLS Secret 一直处于 `Pending`，证书未签发。

**根因：** FDSC Chart 中所有 Ingress 都配置了 `cert-manager.io/cluster-issuer` 注解，依赖 cert-manager 自动签发证书。

**解决方案：**
```bash
helm install cert-manager jetstack/cert-manager \
    --namespace cert-manager --create-namespace \
    --set crds.enabled=true --wait --timeout 5m
```

**验证命令：**
```bash
kubectl get pods -n cert-manager
kubectl get clusterissuer
kubectl get certificates -A
```

---

### 4.4 Keycloak DID 证书算法不匹配

**现象：** Keycloak 启动后，DID 操作失败，日志报错 `signature algorithm not supported` 或 VC 签发失败。

**根因：** cert-manager 默认签发 RSA 证书，但 FDSC 的 DID 操作要求 ECDSA (ES256) 算法。Keycloak 使用 `signingKey.keyAlgorithm: ES256` 配置，需要 ECDSA 私钥。

**解决方案：**
```bash
# 1. 删除旧的 RSA 证书 Secret
kubectl delete secret mp-operations.org-tls -n provider

# 2. 确保 Ingress 注解包含 ECDSA 算法
# provider.yaml 中:
# cert-manager.io/private-key-algorithm: "ECDSA"

# 3. cert-manager 会自动重新签发 ECDSA 证书
# 4. 重启 Keycloak Pod
kubectl delete pod -l app.kubernetes.io/name=keycloak -n provider
```

**验证命令：**
```bash
# 检查证书算法
kubectl get secret mp-operations.org-tls -n provider -o jsonpath='{.data.tls\.crt}' \
    | base64 -d | openssl x509 -text -noout | grep "Signature Algorithm"
# 应输出: ecdsa-with-SHA256
```

---

### 4.5 Verifier init container subPath mount 问题

**现象：** Verifier Pod 的 `add-root-ca` init container 启动失败，报文件挂载错误。

**根因：** Kubernetes 的 subPath mount 在 init container 和主容器之间存在已知的文件系统隔离问题。`/etc/ssl/cert.pem` 使用 `subPath: cert.pem` 挂载时，init container 写入的内容可能不可见。

**解决方案：** 重启 Pod（Kubernetes 会重新执行 init container 并正确挂载）。
```bash
kubectl delete pod -l app.kubernetes.io/name=verifier -n provider
```

**验证命令：**
```bash
kubectl get pods -n provider | grep verifier
kubectl logs -n provider -l app.kubernetes.io/name=verifier -c add-root-ca
```

---

### 4.6 TIL 注册 Job 失败堆积

**现象：** `kubectl get pods -n provider` 显示大量 `til-registration-*` Pod 处于 `Error` 或 `CrashLoopBackOff` 状态。

**根因：** TIL (Trusted Issuers List) 注册 Job 依赖 Verifier 和 TIR 服务就绪。如果这些服务尚未启动，Job 会失败并重试，导致多个失败 Pod 堆积。

**解决方案：**
```bash
# 清理所有失败的 Job Pod
kubectl delete jobs -n provider --field-selector status.successful=0

# 或删除所有失败的 til-registration Pod
kubectl get pods -n provider | grep til-registration | grep -v Running | \
    awk '{print $1}' | xargs kubectl delete pod -n provider
```

**验证命令：**
```bash
kubectl get jobs -n provider
kubectl get pods -n provider | grep til-registration
```

---

### 4.7 Ingress 缺失 ingressClassName

**现象：** 所有 Ingress 返回 404，nginx-ingress-controller 日志显示 `no endpoints available` 或 `ingress not found`。

**根因：** FDSC Chart 的 Ingress 资源默认使用 Traefik 注解（`traefik.ingress.kubernetes.io/router.tls`），但未设置 `spec.ingressClassName`。禁用 Traefik 后，nginx-ingress-controller 需要明确的 `ingressClassName: nginx` 才能识别 Ingress。

**解决方案：**
```bash
# 方法 1: 一次性 patch 所有 Ingress
kubectl get ingress -A -o name | xargs -I {} kubectl patch {} \
    --type merge -p '{"spec":{"ingressClassName":"nginx"}}'

# 方法 2: 在 values.yaml 中为每个组件添加 ingressClassName
# (Chart 较旧版本可能不支持，需要手动 patch)
```

**验证命令：**
```bash
kubectl get ingress -A -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,CLASS:.spec.ingressClassName'
# 所有 Ingress 的 CLASS 列应显示 nginx
```

---

### 4.8 Consumer keystore-password Secret 缺失

**现象：** Consumer Keycloak Pod 启动失败，日志报 `secret "keystore-password" not found`。

**根因：** Consumer Keycloak 的 `prepare-keystore` init container 需要从 `keystore-password` Secret 读取密码来创建 PKCS12 keystore。Chart 不会自动创建这个 Secret。

**解决方案：**
```bash
kubectl create secret generic keystore-password \
    --from-literal=password=changeit \
    -n consumer
```

**验证命令：**
```bash
kubectl get secret keystore-password -n consumer
kubectl get pods -n consumer | grep keycloak
```

---

### 4.9 Contract Management API 404

**现象：** 访问 `contract-management.127.0.0.1.nip.io` 返回 404。

**根因：** Contract Management 服务虽然部署了，但不暴露标准的 negotiation/transfer REST API。它主要通过 TMForum API 的通知机制（`notification.enabled: true`）工作，而不是提供独立的合同协商端点。

**解决方案：** Demo 中用本地 dataclass 模拟 Contract Negotiation 和 Transfer Process 状态流转。
```python
@dataclass
class NegotiationState:
    negotiation_id: str = ""
    state: str = "INITIATED"
    state_history: list = field(default_factory=list)
```

**验证命令：**
```bash
curl -k https://contract-management.127.0.0.1.nip.io/
# 预期: 404 或 401 (服务存在但无公开端点)
```

---

### 4.10 端口占用 (k3s 80/443)

**现象：** nginx-ingress-controller 无法绑定 80/443 端口。

**根因：** k3s Docker 容器已将主机的 80/443 端口映射到容器内部。nginx-ingress-controller 在容器内运行时，端口已被 k3s 的 Service LB 占用。

**解决方案：** 无需额外处理。k3s 的 Service LB 会自动将流量转发到 nginx-ingress-controller 的 ClusterIP。通过 nip.io 域名访问时，请求链路为：
```
主机:80 → k3s 容器:80 → nginx-ingress ClusterIP → Pod
```

**验证命令：**
```bash
# 从主机访问
curl -k https://keycloak-provider.127.0.0.1.nip.io/realms/test-realm
```

---

### 4.11 cert-manager CA Secret 缺失

**现象：** Provider/Consumer 部署后，所有 Certificate 资源处于 `Issuing` 或 `False` 状态，Secret 未创建；`kubectl describe certificate` 显示 `secret ca-secret not found` 或 issuer 不存在。

**根因：** Chart 中 Certificate 引用了 `spec.issuerRef.name: ca-issuer`，而 `ca-issuer` 需要读取名为 `ca-secret` 的 CA 根证书 Secret。cert-manager 默认只安装了 `selfsigned-issuer`，没有生成对应的 CA 证书和 CA issuer。

**解决方案：** 重新创建自签名 CA 证书链：
```bash
kubectl apply -f - <<'EOF'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ca-cert
  namespace: cert-manager
spec:
  isCA: true
  commonName: fiware-dsc-ca
  secretName: ca-secret
  privateKey:
    algorithm: ECDSA
    size: 256
  issuerRef:
    name: selfsigned-issuer
    kind: ClusterIssuer
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: ca-issuer
spec:
  ca:
    secretName: ca-secret
EOF
```

**验证命令：**
```bash
kubectl get clusterissuer selfsigned-issuer ca-issuer
kubectl get secret ca-secret -n cert-manager
kubectl get certificate -A
```

---

### 4.12 MongoDB ServiceAccount 缺失

**现象：** `mongodb-0` Pod 一直 `Pending`，事件显示 `serviceaccount "mongodb-database" not found`。

**根因：** `managedMongo` StatefulSet 模板显式设置了 `serviceAccountName: mongodb-database`，但 Chart 没有自动创建该 ServiceAccount。

**解决方案：**
```bash
kubectl create serviceaccount mongodb-database -n provider
```

**验证命令：**
```bash
kubectl get serviceaccount mongodb-database -n provider
kubectl get pods -n provider | grep mongodb
```

---

### 4.13 MongoDB Agent 镜像拉取失败

**现象：** `mongodb-0` Pod 中 `mongodb-agent` container 处于 `ImagePullBackOff`，镜像 `docker.io/mongodb/mongodb-agent:12.0.15.7648-1` 无法拉取；或拉取后报错 `manifest unknown`。

**根因：** 该镜像 tag 在 Docker Hub 不存在/已移除，且 quay.io 上的替代 tag 命名不同。mongodb-agent 是 MongoDB Community Operator / managedMongo 用来执行自动化任务的 sidecar。

**解决方案：** 如果本地已有 `quay.io/mongodb/mongodb-agent-ubi:<tag>`，可替换 StatefulSet 的镜像：
```bash
# 方案 1：直接修改 StatefulSet 镜像
kubectl set image statefulset/mongodb \
  mongodb-agent=quay.io/mongodb/mongodb-agent-ubi:108.0.6.8796-1 \
  -n provider

# 方案 2：在 provider.yaml 中指定 mongodb-agent 镜像
managedMongo:
  image: "mongodb/mongodb-agent:12.0.15.7648-1"  # 若无法拉取，需手动导入或替换
```

> **注意：** 替换后 `mongodb-0` 可能显示 `1/2 Running`，但 mongod 本身健康，不影响 demo 运行。

**验证命令：**
```bash
kubectl describe pod mongodb-0 -n provider | grep -A5 "Failed to pull image"
kubectl get pod mongodb-0 -n provider
```

---

### 4.14 MongoDB 认证机制不匹配（BAE charging / logic proxy）

**现象：** `provider-biz-ecosystem-charging-backend` 或 `provider-biz-ecosystem-logic-proxy` Pod 反复 `CrashLoopBackOff`，日志显示 `Authentication failed`、`SCRAM-SHA-1 authentication failed` 或 `UserNotFound: Could not find user "charging"@charging_db`。

**根因：**
1. BAE 组件默认使用 `SCRAM-SHA-1`，但 managedMongo 只启用 `SCRAM-SHA-256`。
2. Chart 没有自动创建 `charging` 和 `belp` 两个 MongoDB 用户。

**解决方案：**
1. 进入 `mongodb-0` 容器，以管理员身份连接 mongod 并创建用户：
```bash
kubectl exec -it mongodb-0 -n provider -c mongod -- mongosh \
  "mongodb://root:<password>@localhost:27017/admin?authSource=admin" \
  --eval '
    use charging_db;
    db.createUser({
      user: "charging",
      pwd: "charging_password",
      roles: [{role: "readWrite", db: "charging_db"}]
    });
    use belp_db;
    db.createUser({
      user: "belp",
      pwd: "belp_password",
      roles: [{role: "readWrite", db: "belp_db"}]
    });
  '
```
2. 为 BAE 组件设置环境变量，强制使用 SCRAM-SHA-256：
```yaml
# provider.yaml
biz-ecosystem-charging-backend:
  env:
    BAE_CB_MONGO_AUTH_MECHANISM: "SCRAM-SHA-256"

biz-ecosystem-logic-proxy:
  env:
    BAE_LP_MONGO_AUTH_MECHANISM: "SCRAM-SHA-256"
```

> `root` 密码可通过 `kubectl get secret mongodb-root-credentials -n provider -o jsonpath='{.data.password}' | base64 -d` 获取。

**验证命令：**
```bash
kubectl logs -n provider -l app.kubernetes.io/name=biz-ecosystem-charging-backend
kubectl logs -n provider -l app.kubernetes.io/name=biz-ecosystem-logic-proxy
```

---

### 4.15 Consumer postgres-operator ClusterRole 冲突

**现象：** Consumer Helm install 失败，报错 `resource mapping not found... ClusterRole "postgres-pod" already exists` 或 `cannot patch "postgres-pod"`。

**根因：** `consumer.yaml` 默认启用 `decentralizedIam.vcAuthentication.postgres-operator`，会尝试安装 Zalando PostgreSQL Operator 的 CRD/ClusterRole。而基础设施层已经单独安装了 postgres-operator，导致全局 ClusterRole 冲突。

**解决方案：** 部署 Consumer 时禁用 vcAuthentication 中的 postgres-operator：
```bash
helm install consumer charts/data-space-connector \
    -f k3s/consumer.yaml \
    --namespace consumer --create-namespace --wait --timeout 10m \
    --set decentralizedIam.vcAuthentication.postgres-operator.enabled=false
```

**验证命令：**
```bash
helm list -n consumer
kubectl get pods -n consumer
```

---

### 4.16 Provider Keycloak keystore-password Secret 缺失

**现象：** Provider Keycloak Pod 的 `prepare-keystore` init container 失败，提示 `secret "keystore-password" not found`。

**根因：** 与 Consumer 类似，Provider Keycloak 同样依赖 `keystore-password` Secret，但 Chart 默认不会自动创建（视版本而定）。

**解决方案：**
```bash
kubectl create secret generic keystore-password \
    --from-literal=password=changeit -n provider
```

**验证命令：**
```bash
kubectl get secret keystore-password -n provider
kubectl get pods -n provider | grep keycloak
```

---

### 4.17 k3s 容器重启后的常见问题

**现象 1：** `just up` 报 `Conflict. The container name "/k3s-server" is already in use`。

**根因：** k3s-server 容器之前已创建（当前处于 Exited），`k3s-start` 尝试 `docker run` 同名容器。

**解决方案：** 不要重建容器，直接启动并刷新 kubeconfig：
```bash
docker start k3s-server
docker exec k3s-server cat /etc/rancher/k3s/k3s.yaml > /tmp/k3s.yaml
```

**现象 2：** 刷新 kubeconfig 前执行 `just k3s-wait` 会一直卡住（连不上旧 server 地址）。

**现象 3：** 重启后 `mongodb-0` 长时间显示 `1/2 Running`：`mongod` 容器已 Ready，未就绪的是 `mongodb-agent` sidecar（仅 MongoDB Operator 管理用途）。TMForum / Scorpio 等依赖的是 mongod 本身，不影响 Demo 运行（另见 4.13）。

**验证命令：**
```bash
kubectl --kubeconfig=/tmp/k3s.yaml get nodes                          # Ready
kubectl --kubeconfig=/tmp/k3s.yaml -n provider get pod mongodb-0 \
  -o jsonpath='{range .status.containerStatuses[*]}{.name} ready={.ready}{"\n"}{end}'
# 预期: mongod ready=true
```

---

## 5. 配置参考

### 5.1 provider.yaml 关键配置

```yaml
# cert-manager 算法 (必须 ECDSA)
cert-manager.io/private-key-algorithm: "ECDSA"

# Keycloak DID 签名算法
keycloak:
  signingKey:
    keyAlgorithm: ES256
    did: did:web:shenyousota.github.io:dssc-toolbox

# MongoDB: 使用 managedMongo (非 Operator)
mongo-operator:
  enabled: false
managedMongo:
  enabled: true

# Verifier DID 配置
decentralizedIam:
  vcAuthentication:
    vcverifier:
      deployment:
        verifier:
          did: did:web:shenyousota.github.io:dssc-toolbox
          requestKeyAlgorithm: ES256
```

### 5.2 consumer.yaml 关键配置

```yaml
# 仅启用 Consumer 所需组件
decentralizedIam:
  enabled: true
  vcAuthentication:
    vcverifier:
      enabled: false
    credentials-config-service:
      enabled: false
    trusted-issuers-list:
      enabled: false
  odrlAuthorization:
    enabled: false

# DID
did:
  enabled: true
  config:
    server:
      hostUrl: "http://fancy-marketplace.biz"

# 禁用不需要的组件
tm-forum-api:
  enabled: false
contract-management:
  enabled: false
scorpio:
  enabled: false
```

### 5.3 Secret 管理

| Secret | Namespace | 用途 | 创建方式 |
|--------|-----------|------|---------|
| `keystore-password` | provider | Keycloak PKCS12 keystore 密码 | **手动创建** |
| `keystore-password` | consumer | Keycloak PKCS12 keystore 密码 | **手动创建** |
| `ca-secret` | cert-manager | cert-manager CA 根证书 | 手动创建 CA 证书链 |
| `mp-operations.org-tls` | provider | Provider DID 证书 (ECDSA) | cert-manager 签发 |
| `fancy-marketplace.biz-tls` | consumer | Consumer DID 证书 (ECDSA) | cert-manager 签发 |
| `verifier.mp-operations.org-tls` | provider | Verifier 签名证书 | cert-manager 签发 |

---

## 6. 快速排查速查表

| 症状 | 可能原因 | 排查命令 | 解决方案 |
|------|---------|---------|---------|
| Pod `ImagePullBackOff` | 镜像拉取超时 | `kubectl describe pod <name>` | 等待/换镜像源 |
| Pod `Pending` (PVC) | StorageClass 或 Operator 缺失 | `kubectl describe pvc -A` | 安装 PostgreSQL Operator |
| Pod `CrashLoop` (Keycloak) | Secret 缺失 | `kubectl logs <pod>` | 创建 `keystore-password` |
| Ingress 404 | ingressClassName 缺失 | `kubectl get ingress -A` | patch ingressClassName |
| TLS 证书 Pending | cert-manager 未安装 / CA issuer 缺失 | `kubectl get certificates -A` | 安装 cert-manager + 创建 CA issuer |
| DID 签名失败 | 证书算法 RSA (需 ECDSA) | `openssl x509 -text` | 删除旧 Secret，重新签发 |
| Verifier 启动失败 | subPath mount 问题 | `kubectl logs <pod> -c add-root-ca` | 重启 Pod |
| TIL Job 堆积 | 依赖服务未就绪 | `kubectl get jobs -A` | 清理失败 Job |
| Scorpio 查询 400 | 空查询返回 400 (正常) | `curl <scorpio>/ngsi-ld/v1/entities` | 非错误，服务正常 |
| TMForum 无数据 | 未创建 ProductOffering | `curl <tmf>/productOffering` | Demo 中自动创建 |
| Contract API 404 | 服务不暴露 REST API | `curl -k <contract-mgmt>/` | 本地 dataclass 模拟 |
| Token endpoint 格式差异 | Consumer 用 legacy 格式 | `curl <kc>/realms/<realm>` | 检查 `token-service` 字段 |
| MongoDB `Pending` | ServiceAccount 缺失 | `kubectl get events -n provider` | 创建 `mongodb-database` SA |
| MongoDB agent 拉取失败 | 镜像 tag 不存在 | `kubectl describe pod mongodb-0 -n provider` | 替换为本地已有 agent 镜像 |
| BAE charging/logic CrashLoop | SCRAM-SHA-1/256 不匹配或用户缺失 | `kubectl logs <pod> -n provider` | 创建用户 + 设置 `MONGO_AUTH_MECHANISM=SCRAM-SHA-256` |
| Consumer 安装失败 | postgres-operator ClusterRole 冲突 | `helm install ...` 报错 | 加 `--set decentralizedIam.vcAuthentication.postgres-operator.enabled=false` |
| `just up` 报容器名冲突 | k3s-server 容器已存在但停止 | `docker ps -a | grep k3s` | `docker start k3s-server` + 刷新 `/tmp/k3s.yaml` |
| `just k3s-wait` 卡住 | 容器重启后 kubeconfig 失效 | `kubectl get nodes` 超时 | 重新导出 `/tmp/k3s.yaml` |
| `mongodb-0` 一直 `1/2` | mongodb-agent sidecar 未就绪（mongod 正常） | `kubectl get pod mongodb-0 -n provider -o jsonpath=...` | 无需处理，不影响 Demo |
| `POST /productOffering` 400 | term 缺 `@schemaLocation` 或含 `externalId` | 查看返回 `errors[].message` | 加 schemaLocation；移除 externalId（见 Demo 文档 3.2.7/3.2.8） |

---

## 7. 与 FIWARE DSC 的对应关系

| 部署组件 | FIWARE DSC 角色 | 说明 |
|---------|----------------|------|
| Keycloak + DID Helper | 凭证签发 | Consumer 和 Provider 各自部署 |
| VCVerifier + CCS + TIL | 认证框架 | 仅 Provider 部署 |
| APISIX + OPA + ODRL-PAP | 授权框架 | 仅 Provider 部署 |
| TMForum API | 产品目录 | 数据 Offering 管理 |
| Scorpio | 数据服务 | NGSI-LD Context Broker |
| Contract Management | 合同管理 | 当前未完全配置 |
| TIR (Trust Anchor) | 信任锚点 | 独立命名空间，中立运营 |

---

## 7.5 公网 did.json 托管（固定密钥方案）

**问题：** `did:web:shenyousota.github.io:dssc-toolbox` 只在集群内可解析（nip.io / CoreDNS），公网 DNS 不存在该域名，外部组无法无感验证；且 cert-manager 每次随机签发密钥，集群重建后公钥变化，任何人（包括换机器的自己）都无法复现签名。

**方案：** 仓库提交一把固定的 P-256 demo 密钥对（虚构主体，无真实价值），did.json 由公钥确定性生成并发布到 GitHub Pages，集群导入同一把私钥替代 cert-manager 随机签发。

**已定稿身份（2026-08-17 全组确认）：**
- DID：`did:web:shenyousota.github.io:dssc-toolbox`（GitHub Pages project site，仓库根 `did.json`）
- kid：`did:web:shenyousota.github.io:dssc-toolbox#key-1`
- 算法：ES256 / EC P-256，密钥见 `demo/data/keys/`
- 解析 URL：https://shenyousota.github.io/dssc-toolbox/did.json

**工具：** `demo/did_identity.py`（justfile 中有对应任务）：

```bash
just did-keygen         # 一次性生成密钥对 -> demo/data/keys/ (已提交)
just did-export <did>   # 由公钥生成 did.json -> 仓库根 (/.well-known/ 或 /did.json)
just did-cert           # 生成 demo CA + 叶子证书链 -> demo/data/keys/ (供 x5c 用)
just did-export-x5c <did>  # 生成带 x5c 证书链的 did.json (Gaia-X 信任锚试探)
just did-k8s-secret     # 输出导入 k3s 的 kubectl 命令
just did-verify <did>   # 校验公网 did.json 与本地私钥匹配
```

**did.json 当前内容（2026-08-18 起）：** JWK 含 `alg: "ES256"` 和 `x5c` 证书链（叶子 + demo CA，叶子 SAN 为 DID，公钥与 JWK 一致）。x5c 只放在 DID 文档中，**密钥材料不变，已签发的 VC/VP-JWT 无需重签**。证书链文件：`demo/data/keys/demo-ca.key`、`demo-ca.crt`、`provider-leaf.crt`。

**Gaia-X Compliance L3 信任锚（跨组联调已知限制）：** Gaia-X Credential Format 要求 verification method 携带 X.509 证书链（x5c/x5u）并声明 `alg`，裸 JWK 会在 L3 信任锚校验被拦截（B 组实测：5 个用例卡 L3、1 个卡 L2，内容层错误全部被前置屏蔽）。嵌入自签 x5c 是格式层试探——自签 CA 不在公开 trust store 中，锚定校验预计仍失败；要完整跑通需自托管 GXDCH 并把 demo CA 加进其 trust store（未纳入本轮交付）。验签证据以公网 did.json + ES256 本地验签为准。

**did:web 路径规则（容易踩坑）：** 裸域名 `did:web:example.com` → `https://example.com/.well-known/did.json`；带路径 `did:web:org.github.io:repo` → `https://org.github.io/repo/did.json`（**没有 .well-known**）。GitHub Pages project site 用后者，did.json 放仓库根即可，无需买域名。

**发布步骤：**
1. `just did-export` 生成 did.json 并提交 push（本仓库默认分支为 `master`）
2. 仓库 Settings → Pages → Source: Deploy from a branch → master / (root)
3. `just did-verify` 确认公网解析与私钥匹配

注意：GitHub Pages CDN 有缓存，push 后 curl 旧属正常，用带参数 URL（如 `?v=$(date +%s)`）确认新版本已生效。

**集群导入固定密钥（替代 cert-manager 签发的 `mp-operations.org-tls`）：**
```bash
kubectl --kubeconfig=/tmp/k3s.yaml delete secret mp-operations.org-tls -n provider
kubectl --kubeconfig=/tmp/k3s.yaml create secret tls mp-operations.org-tls \
    --cert=demo/data/keys/tls.crt --key=demo/data/keys/tls.key -n provider
```
Keycloak signingKey、did helper、marketplace SIOP 都引用该 secret（见 provider.yaml 5.1/5.3），导入后重启相关 Pod 即可。若最终 DID 改为公网版，需同步修改 provider.yaml 中所有 `did:web:shenyousota.github.io:dssc-toolbox` 出现处及 `did.config.server.hostUrl`。

**安全说明：** `demo/data/keys/` 中的私钥标注了 DEMO KEY，仅限教学 demo；生产环境严禁提交私钥。

---

## 8. 相关文档

- [架构与通信流程](../demo/ARCHITECTURE.md)
- [README](../demo/README.md)
- [数据交换 Demo](./A_data_exchange_demo.md)
- [项目概述](../wiki/1-xiang-mu-gai-shu.md)
- [快速部署指南](../wiki/2-kuai-su-bu-shu-zhi-nan.md)
