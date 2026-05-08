#!/bin/bash
# ============================================================
# DataHub 一键部署脚本 (PostgreSQL 版)
# 适用于 Alibaba Cloud Linux 3 / CentOS 8 / RHEL 8
# ============================================================

set -e

PROJECT_DIR="/opt/neau-data-hub"
COMPOSE_FILE="docker-compose.pg.yml"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ============================================================
# 1. 检查环境
# ============================================================
info "检查运行环境..."

if [ "$(id -u)" -ne 0 ]; then
    error "请使用 root 用户运行此脚本"
fi

if [ ! -d "$PROJECT_DIR" ]; then
    error "项目目录不存在: $PROJECT_DIR，请先将代码克隆到该目录"
fi

cd "$PROJECT_DIR"

if [ ! -f "$COMPOSE_FILE" ]; then
    error "找不到 $COMPOSE_FILE"
fi

# ============================================================
# 2. 安装 Docker（如未安装）
# ============================================================
if ! command -v docker &> /dev/null; then
    info "安装 Docker..."
    yum install -y yum-utils
    yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl start docker
    systemctl enable docker
    info "Docker 安装完成"
else
    info "Docker 已安装: $(docker --version)"
fi

# ============================================================
# 3. 安装 docker-compose（如未安装）
# ============================================================
if ! command -v docker-compose &> /dev/null; then
    if docker compose version &> /dev/null; then
        info "使用 docker compose 插件模式"
        COMPOSE_CMD="docker compose"
    else
        info "安装 docker-compose..."
        curl -L "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-$(uname -s)-$(uname -m)" \
            -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        COMPOSE_CMD="docker-compose"
        info "docker-compose 安装完成"
    fi
else
    COMPOSE_CMD="docker-compose"
    info "docker-compose 已安装: $(docker-compose --version)"
fi

# ============================================================
# 4. 配置 Docker 镜像加速
# ============================================================
if [ ! -f /etc/docker/daemon.json ]; then
    info "配置 Docker 镜像加速..."
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.1ms.run"
  ]
}
EOF
    systemctl daemon-reload
    systemctl restart docker
    info "镜像加速配置完成"
else
    info "Docker daemon.json 已存在，跳过镜像加速配置"
fi

# ============================================================
# 5. 启动服务
# ============================================================
info "开始构建并启动服务（首次构建较慢，请耐心等待）..."

$COMPOSE_CMD -f "$COMPOSE_FILE" up -d --build

info "等待服务启动..."
sleep 10

# 检查容器状态
info "检查容器状态:"
$COMPOSE_CMD -f "$COMPOSE_FILE" ps

# ============================================================
# 6. 等待 PostgreSQL 就绪后导入数据
# ============================================================
info "等待 PostgreSQL 完全就绪..."

MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if docker exec ruoyi-pg pg_isready -U postgres &> /dev/null; then
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    warn "PostgreSQL 启动超时，数据导入跳过。请手动执行数据导入。"
else
    info "PostgreSQL 已就绪，开始导入农业数据..."

    # 检查 Python3 和依赖
    if ! command -v python3 &> /dev/null; then
        info "安装 Python3..."
        yum install -y python3 python3-pip
    fi

    # 安装数据导入依赖
    pip3 install -q psycopg2-binary pandas openpyxl xlrd

    # 检查 data 目录是否存在
    if [ -d "$PROJECT_DIR/data" ]; then
        info "执行数据导入（跳过大文件以加快首次部署）..."
        python3 "$PROJECT_DIR/scripts/import_data.py" \
            --data-dir "$PROJECT_DIR/data" \
            --host 127.0.0.1 \
            --port 15432 \
            --user postgres \
            --password root \
            --db ruoyi-fastapi \
            --skip-large

        if [ $? -eq 0 ]; then
            info "数据导入完成！"
        else
            warn "数据导入过程中出现错误，请检查日志后手动重试"
        fi
    else
        warn "data 目录不存在，跳过数据导入"
        warn "如需导入数据，请将 data 目录放到 $PROJECT_DIR/ 下后执行："
        warn "  python3 $PROJECT_DIR/scripts/import_data.py --data-dir $PROJECT_DIR/data --host 127.0.0.1 --port 15432 --user postgres --password root --db ruoyi-fastapi"
    fi
fi

# ============================================================
# 7. 输出结果
# ============================================================
echo ""
echo "============================================================"
echo -e "${GREEN}  部署完成！${NC}"
echo "============================================================"
echo ""
echo "  访问地址:  http://$(hostname -I | awk '{print $1}'):12580"
echo "  默认账号:  admin"
echo "  默认密码:  admin123"
echo ""
echo "  服务端口:"
echo "    前端:       12580"
echo "    后端API:    19099"
echo "    PostgreSQL: 15432"
echo "    Redis:      16379"
echo ""
echo "  常用命令:"
echo "    查看状态:   $COMPOSE_CMD -f $PROJECT_DIR/$COMPOSE_FILE ps"
echo "    查看日志:   $COMPOSE_CMD -f $PROJECT_DIR/$COMPOSE_FILE logs -f"
echo "    重启服务:   $COMPOSE_CMD -f $PROJECT_DIR/$COMPOSE_FILE restart"
echo "    停止服务:   $COMPOSE_CMD -f $PROJECT_DIR/$COMPOSE_FILE down"
echo ""
echo "  注意: 请在阿里云安全组中放行 12580 端口"
echo "============================================================"
