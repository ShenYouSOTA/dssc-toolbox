# FIWARE DSC Local Deployment Justfile
# 使用方法: just <recipe>

# 默认列出所有命令
default:
    @just --list

# ============================================================
# 环境检查
# ============================================================

# 检查所有必需工具
check:
    @echo "🔍 检查环境..."
    @docker --version
    @helm version --short
    @kubectl version --client --short 2>/dev/null || echo "kubectl: not installed"
    @echo "✅ 环境检查完成"

# ============================================================
# k3s 集群管理
# ============================================================

# 启动 k3s 集群 (Docker 方式)
k3s-start:
    @echo "🚀 启动 k3s 集群..."
    @docker info > /dev/null 2>&1 || (echo "❌ Docker 未运行，请先启动 Docker Desktop" && exit 1)
    docker run -d --name k3s-server \
        --privileged \
        -p 6443:6443 \
        -p 80:80 \
        -p 443:443 \
        -v k3s-data:/var/lib/rancher/k3s \
        rancher/k3s:latest server \
        --disable=traefik
    @echo "⏳ 等待 k3s 启动..."
    @sleep 10
    @echo "📋 获取 kubeconfig..."
    @docker exec k3s-server cat /etc/rancher/k3s/k3s.yaml > /tmp/k3s.yaml
    @sed -i 's/127.0.0.1/localhost/g' /tmp/k3s.yaml
    @echo "✅ k3s 已启动"
    @echo "运行: export KUBECONFIG=/tmp/k3s.yaml"

# 停止 k3s 集群
k3s-stop:
    @echo "🛑 停止 k3s 集群..."
    docker stop k3s-server && docker rm k3s-server
    @echo "✅ k3s 已停止"

# 查看 k3s 状态
k3s-status:
    @docker ps | grep k3s-server || echo "k3s 未运行"

# 获取 kubeconfig
k3s-kubeconfig:
    @docker exec k3s-server cat /etc/rancher/k3s/k3s.yaml

# 等待 k3s 就绪
k3s-wait:
    @echo "⏳ 等待 k3s 就绪..."
    @until kubectl --kubeconfig=/tmp/k3s.yaml get nodes 2>/dev/null | grep -q " Ready"; do sleep 2; done
    @echo "✅ k3s 就绪"

# ============================================================
# 基础设施部署 (cert-manager, postgres-operator)
# ============================================================

# 部署 cert-manager
deploy-cert-manager:
    @echo "📦 部署 cert-manager..."
    helm repo add jetstack https://charts.jetstack.io 2>/dev/null || true
    helm repo update
    helm install cert-manager jetstack/cert-manager \
        --namespace cert-manager --create-namespace \
        --set crds.enabled=true \
        --wait --timeout 5m
    @echo "✅ cert-manager 部署完成"

# 部署 PostgreSQL Operator
deploy-postgres-operator:
    @echo "🐘 部署 PostgreSQL Operator..."
    helm repo add postgres-operator https://opensource.zalando.com/postgres-operator/charts/postgres-operator 2>/dev/null || true
    helm repo update
    kubectl create namespace postgres-operator 2>/dev/null || true
    helm install postgres-operator postgres-operator/postgres-operator \
        --namespace postgres-operator \
        --wait --timeout 5m
    @echo "✅ PostgreSQL Operator 部署完成"

# 部署所有基础设施
deploy-infra: deploy-cert-manager deploy-postgres-operator
    @echo "✅ 基础设施部署完成"

# ============================================================
# Helm 操作
# ============================================================

# 更新 Helm 依赖
helm-deps:
    @echo "📦 更新 Helm 依赖..."
    cd data-space-connector && helm dependency update charts/data-space-connector
    @echo "✅ 依赖更新完成"

# 渲染模板 (验证配置)
helm-template provider="provider":
    @echo "🔧 渲染 {{provider}} 模板..."
    cd data-space-connector && helm template {{provider}} charts/data-space-connector \
        -f k3s/{{provider}}.yaml \
        --namespace {{provider}} \
        --dry-run

# ============================================================
# 部署操作
# ============================================================

# 部署 Trust Anchor
deploy-trust-anchor:
    @echo "🏛️ 部署 Trust Anchor..."
    cd data-space-connector && helm install trust-anchor charts/trust-anchor \
        -f k3s/trust-anchor.yaml \
        --namespace trust-anchor \
        --create-namespace \
        --wait --timeout 5m
    @echo "✅ Trust Anchor 部署完成"

# 部署 Provider
deploy-provider:
    @echo "🏢 部署 Provider..."
    cd data-space-connector && helm install provider charts/data-space-connector \
        -f k3s/provider.yaml \
        --namespace provider \
        --create-namespace \
        --wait --timeout 10m
    @echo "✅ Provider 部署完成"

# 部署 Consumer (处理 ClusterRole 冲突)
deploy-consumer:
    @echo "👥 部署 Consumer..."
    @kubectl create secret generic keystore-password --from-literal=password=changeit -n consumer 2>/dev/null || true
    cd data-space-connector && helm install consumer charts/data-space-connector \
        -f k3s/consumer.yaml \
        --namespace consumer \
        --create-namespace \
        --wait --timeout 10m
    @echo "✅ Consumer 部署完成"

# 部署所有应用组件 (不含基础设施)
deploy-apps: deploy-trust-anchor deploy-provider deploy-consumer
    @echo "✅ 应用组件部署完成"

# ============================================================
# 一键启动 (完整流程)
# ============================================================

# 完整启动: k3s → 基础设施 → 应用 → 检查
up: k3s-start k3s-wait deploy-infra deploy-apps smoke-test
    @echo ""
    @echo "🎉🎉🎉 Data Space Connector 启动完成! 🎉🎉🎉"
    @echo ""
    @echo "运行 Demo:"
    @echo "  just demo-cluster        # 真实集群 Demo"
    @echo "  just demo-python         # Mock Demo"
    @echo ""
    @echo "调试:"
    @echo "  just pods                # 查看所有 Pod"
    @echo "  just logs <pod>          # 查看 Pod 日志"
    @echo "  just demo-cluster-health # 健康检查"

# 重新部署 (不重启 k3s)
redeploy: uninstall-all deploy-infra deploy-apps smoke-test
    @echo "✅ 重新部署完成"

# ============================================================
# 状态查看
# ============================================================

# 查看所有 Pod
pods:
    @kubectl --kubeconfig=/tmp/k3s.yaml get pods -A

# 查看所有服务
services:
    @kubectl --kubeconfig=/tmp/k3s.yaml get svc -A

# 查看所有 Helm releases
releases:
    @helm --kubeconfig=/tmp/k3s.yaml list -A

# 查看特定命名空间的 Pod
pods-ns ns:
    @kubectl --kubeconfig=/tmp/k3s.yaml get pods -n {{ns}} -o wide

# 查看 Provider Pod
pods-provider:
    @kubectl --kubeconfig=/tmp/k3s.yaml get pods -n provider -o wide

# 查看 Consumer Pod
pods-consumer:
    @kubectl --kubeconfig=/tmp/k3s.yaml get pods -n consumer -o wide

# ============================================================
# 调试 / 日志
# ============================================================

# 查看 Pod 日志
logs pod:
    @kubectl --kubeconfig=/tmp/k3s.yaml logs {{pod}} -A --tail=50

# 查看 Pod 日志 (指定命名空间)
logs-ns ns pod:
    @kubectl --kubeconfig=/tmp/k3s.yaml logs {{pod}} -n {{ns}} --tail=50

# 查看 Provider Keycloak 日志
logs-keycloak:
    @kubectl --kubeconfig=/tmp/k3s.yaml logs -n provider -l app.kubernetes.io/name=keycloak --tail=50

# 查看 Provider Verifier 日志
logs-verifier:
    @kubectl --kubeconfig=/tmp/k3s.yaml logs -n provider -l app.kubernetes.io/name=verifier --tail=50

# 查看 MongoDB 日志
logs-mongodb:
    @kubectl --kubeconfig=/tmp/k3s.yaml logs -n provider mongodb-0 --tail=50

# 查看 PostgreSQL 日志
logs-postgres:
    @kubectl --kubeconfig=/tmp/k3s.yaml logs -n provider postgres-0 --tail=50

# 查看 Pod 事件
events ns="provider":
    @kubectl --kubeconfig=/tmp/k3s.yaml get events -n {{ns}} --sort-by='.lastTimestamp' | tail -20

# 查看 Pod 详情
describe pod ns="provider":
    @kubectl --kubeconfig=/tmp/k3s.yaml describe pod {{pod}} -n {{ns}}

# 进入 Pod shell
exec pod ns="provider":
    @kubectl --kubeconfig=/tmp/k3s.yaml exec -it {{pod}} -n {{ns}} -- /bin/sh

# ============================================================
# Smoke Test
# ============================================================

# 快速 Smoke Test (检查关键 Pod 是否 Running)
smoke-test:
    @echo "🧪 Smoke Test..."
    @echo ""
    @echo "  [Trust Anchor]"
    @kubectl --kubeconfig=/tmp/k3s.yaml get pods -n trust-anchor --no-headers 2>/dev/null | awk '{print "    " $$1 ": " $$3}'
    @echo ""
    @echo "  [Provider]"
    @kubectl --kubeconfig=/tmp/k3s.yaml get pods -n provider --no-headers 2>/dev/null | awk '{print "    " $$1 ": " $$3}'
    @echo ""
    @echo "  [Consumer]"
    @kubectl --kubeconfig=/tmp/k3s.yaml get pods -n consumer --no-headers 2>/dev/null | awk '{print "    " $$1 ": " $$3}'
    @echo ""
    @kubectl --kubeconfig=/tmp/k3s.yaml get pods -A --no-headers 2>/dev/null | awk '{print $$3}' | grep -cvE "Running|Completed" | awk '{if ($$1 > 0) print "  ⚠️  " $$1 " 个 Pod 异常"; else print "  ✅ 所有 Pod 正常"}'

# ============================================================
# 清理操作
# ============================================================

# 卸载所有 Helm release
uninstall-all:
    @echo "🧹 卸载所有组件..."
    -helm --kubeconfig=/tmp/k3s.yaml uninstall consumer -n consumer 2>/dev/null
    -helm --kubeconfig=/tmp/k3s.yaml uninstall provider -n provider 2>/dev/null
    -helm --kubeconfig=/tmp/k3s.yaml uninstall trust-anchor -n trust-anchor 2>/dev/null
    -helm --kubeconfig=/tmp/k3s.yaml uninstall postgres-operator -n postgres-operator 2>/dev/null
    -helm --kubeconfig=/tmp/k3s.yaml uninstall cert-manager -n cert-manager 2>/dev/null
    @echo "✅ 卸载完成"

# 删除命名空间
clean-namespaces:
    @echo "🧹 删除命名空间..."
    -kubectl --kubeconfig=/tmp/k3s.yaml delete namespace consumer provider trust-anchor postgres-operator cert-manager 2>/dev/null
    @echo "✅ 命名空间删除完成"

# 完全清理
clean: uninstall-all clean-namespaces
    @echo "🎉 完全清理完成"

# 停止集群 (关机前执行，保留镜像缓存)
down: clean k3s-stop
    @echo ""
    @echo "🛑 集群已停止"
    @echo ""
    @echo "镜像缓存保留在 k3s-data 卷中，下次启动无需重新拉取。"
    @echo "重启: just k3s-start && export KUBECONFIG=/tmp/k3s.yaml && just up"

# 重置 (清理 + 重启)
reset: clean k3s-stop k3s-start up
    @echo "✅ 重置完成"

# ============================================================
# 演示操作 (Mock Demo - 不依赖集群)
# ============================================================

# 运行 Python 数据交换演示
demo-python:
    @echo "🐍 运行 Python Mock 演示..."
    cd demo && uv run python run_demo.py

# 运行 Python Provider 服务器
demo-provider:
    @echo "🏢 启动 Python Provider..."
    cd demo && uv run python run_demo.py server

# 运行完整 Mock Demo 并保存日志
demo-run:
    @echo "🚀 运行完整 Mock Demo 并保存日志..."
    @mkdir -p demo/logs
    cd demo && uv run python run_demo.py 2>&1 | tee "logs/demo-$(date +%Y%m%d-%H%M%S).log"
    @echo "✅ 日志已保存到 demo/logs/"

# 运行 Demo (仅 Consumer 客户端)
demo-client:
    @echo "👤 运行 Consumer 客户端..."
    cd demo && uv run python run_demo.py client

# 运行 Demo (按建筑ID过滤)
demo-building building_id:
    @echo "🏢 查询建筑 {{building_id}}..."
    cd demo && uv run python run_demo.py client --building-id {{building_id}}

# ============================================================
# 演示操作 (真实集群 Demo - 依赖集群)
# ============================================================

# 运行真实集群端到端 Demo
demo-cluster:
    @echo "🚀 运行真实集群 Demo..."
    @mkdir -p demo/logs
    cd demo && uv run python demo_real_cluster.py full 2>&1 | tee "logs/demo-real-$(date +%Y%m%d-%H%M%S).log"

# 真实集群健康检查
demo-cluster-health:
    @echo "📡 集群健康检查..."
    cd demo && uv run python demo_real_cluster.py health

# 启动 port-forward (手动测试)
demo-cluster-pf:
    @echo "🔌 启动 port-forward..."
    cd demo && uv run python demo_real_cluster.py pf

# ============================================================
# DID 身份 (公网 did.json 托管)
# ============================================================

# 生成固定 demo 密钥对 (一次性, 提交进仓库)
did-keygen:
    @echo "🔑 生成 Provider demo 密钥对..."
    cd demo && uv run python did_identity.py keygen

# 由公钥生成 did.json (发布到 GitHub Pages)
did-export did="did:web:shenyousota.github.io:dssc-toolbox":
    @echo "📄 生成 did.json..."
    cd demo && uv run python did_identity.py did --did {{did}}

# 生成 demo CA + 叶子证书链 (供 x5c 嵌入 did.json)
did-cert:
    @echo "📜 生成 demo 证书链..."
    cd demo && uv run python did_identity.py cert

# 生成带 x5c 证书链的 did.json (Gaia-X 信任锚试探)
did-export-x5c did="did:web:shenyousota.github.io:dssc-toolbox":
    @echo "📄 生成带 x5c 的 did.json..."
    cd demo && uv run python did_identity.py did --did {{did}} --x5c

# 托管 PEM 证书链并生成 x5u 引用的 did.json (验签方 OpenSSL 解析 x5c 失败时用)
did-export-x5u did="did:web:shenyousota.github.io:dssc-toolbox":
    @echo "📄 生成 x5u 版 did.json + x5c-chain.pem..."
    cd demo && uv run python did_identity.py did --did {{did}} --x5u

# 输出把固定密钥导入 k3s 的命令 (替代 cert-manager 随机签发)
did-k8s-secret:
    cd demo && uv run python did_identity.py k8s-secret

# 校验公网 did.json 与本地私钥匹配
did-verify did="did:web:shenyousota.github.io:dssc-toolbox":
    @echo "🔍 校验公网 did.json..."
    cd demo && uv run python did_identity.py verify --did {{did}}

# ============================================================
# 文档
# ============================================================

# 打开项目文档
docs:
    @echo "📖 项目文档:"
    @echo "  - 项目概述: wiki/1-xiang-mu-gai-shu.md"
    @echo "  - 部署指南: wiki/2-kuai-su-bu-shu-zhi-nan.md"
    @echo "  - 部署笔记: demo/A_fiware_deployment_notes.md"
    @echo "  - Python演示: demo/README.md"
    @echo "  - 排查记录: doc/troubleshooting-k3s-deployment.md"
