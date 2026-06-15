#!/usr/bin/env bash
# ============================================================
# NEAU DataHub 一键部署脚本 (PostgreSQL 版)
# 支持交互选择：构建前端、构建后端、启动数据库、导入数据等
# ============================================================

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.pg.yml}"

FRONTEND_SERVICE="${FRONTEND_SERVICE:-ruoyi-frontend}"
BACKEND_SERVICE="${BACKEND_SERVICE:-ruoyi-backend-pg}"
PG_SERVICE="${PG_SERVICE:-ruoyi-pg}"
REDIS_SERVICE="${REDIS_SERVICE:-ruoyi-redis}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
note() { echo -e "${BLUE}[NOTE]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

cd "$PROJECT_DIR"

[ -f "$COMPOSE_FILE" ] || error "找不到 $PROJECT_DIR/$COMPOSE_FILE"

detect_compose() {
    if docker compose version >/dev/null 2>&1; then
        COMPOSE_CMD=(docker compose)
    elif command -v docker-compose >/dev/null 2>&1; then
        COMPOSE_CMD=(docker-compose)
    else
        error "未找到 docker compose 或 docker-compose，请先安装 Docker Compose"
    fi
}

compose() {
    "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" "$@"
}

require_docker() {
    command -v docker >/dev/null 2>&1 || error "未找到 docker，请先安装 Docker"
    if ! docker info >/dev/null 2>&1; then
        error "Docker 未运行，或当前用户无权限访问 Docker"
    fi
    detect_compose
}

ensure_dirs() {
    mkdir -p data_assets
    mkdir -p pgdata
    mkdir -p redisdata
}

show_header() {
    echo ""
    echo "============================================================"
    echo "  NEAU DataHub 部署菜单"
    echo "============================================================"
    echo "  项目目录:     $PROJECT_DIR"
    echo "  Compose文件:  $COMPOSE_FILE"
    echo "  前端服务:     $FRONTEND_SERVICE"
    echo "  后端服务:     $BACKEND_SERVICE"
    echo "  数据库服务:   $PG_SERVICE"
    echo "  Redis服务:    $REDIS_SERVICE"
    echo "============================================================"
}

show_status() {
    info "容器状态:"
    compose ps
}

show_urls() {
    local host_ip
    host_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    [ -n "$host_ip" ] || host_ip="127.0.0.1"

    echo ""
    echo "============================================================"
    echo -e "${GREEN}  操作完成${NC}"
    echo "============================================================"
    echo "  访问地址:  http://$host_ip:12580"
    echo "  默认账号:  admin"
    echo "  默认密码:  admin123"
    echo ""
    echo "  常用命令:"
    echo "    查看状态:   $0 status"
    echo "    查看日志:   $0 logs"
    echo "    重启全部:   $0 restart"
    echo "============================================================"
}

wait_pg_ready() {
    info "等待 PostgreSQL 就绪..."
    local max_wait="${1:-90}"
    local waited=0
    while [ "$waited" -lt "$max_wait" ]; do
        if docker exec "$PG_SERVICE" pg_isready -U postgres >/dev/null 2>&1; then
            info "PostgreSQL 已就绪"
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
    done
    error "PostgreSQL 在 ${max_wait}s 内未就绪"
}

start_infra() {
    ensure_dirs
    info "启动数据库和 Redis，不会删除 pgdata"
    compose up -d "$PG_SERVICE" "$REDIS_SERVICE"
    wait_pg_ready 90
    show_status
}

start_all_no_build() {
    ensure_dirs
    info "启动全部服务，不重新构建镜像"
    compose up -d
    show_status
    show_urls
}

rebuild_frontend() {
    require_docker
    ensure_dirs
    info "重新构建前端: $FRONTEND_SERVICE"
    compose build "$FRONTEND_SERVICE"
    compose up -d "$FRONTEND_SERVICE"
    show_status
    show_urls
}

rebuild_backend() {
    require_docker
    ensure_dirs
    info "启动数据库和 Redis，确保后端依赖服务可用"
    compose up -d "$PG_SERVICE" "$REDIS_SERVICE"
    wait_pg_ready 90

    info "重新构建后端: $BACKEND_SERVICE"
    DOCKER_BUILDKIT=1 compose build "$BACKEND_SERVICE"
    compose up -d "$BACKEND_SERVICE"
    show_status
    show_urls
}

rebuild_app() {
    require_docker
    ensure_dirs
    info "重新构建前端和后端"
    compose up -d "$PG_SERVICE" "$REDIS_SERVICE"
    wait_pg_ready 90
    DOCKER_BUILDKIT=1 compose build "$BACKEND_SERVICE"
    compose build "$FRONTEND_SERVICE"
    compose up -d "$BACKEND_SERVICE" "$FRONTEND_SERVICE"
    show_status
    show_urls
}

full_deploy() {
    require_docker
    ensure_dirs
    info "完整部署：构建并启动全部服务，不导入农业数据"
    DOCKER_BUILDKIT=1 compose up -d --build
    show_status
    show_urls
}

import_data() {
    require_docker
    ensure_dirs
    compose up -d "$PG_SERVICE" "$REDIS_SERVICE" "$BACKEND_SERVICE"
    wait_pg_ready 90

    if [ ! -d "$PROJECT_DIR/data" ]; then
        warn "data 目录不存在，跳过导入"
        return 0
    fi

    warn "导入会向现有数据库写入/更新农业数据，但不会删除 pgdata"
    read -r -p "确认执行数据导入？输入 yes 继续: " confirm
    if [ "$confirm" != "yes" ]; then
        warn "已取消数据导入"
        return 0
    fi

    info "在后端容器中执行导入脚本（默认 --skip-large）"
    docker exec "$BACKEND_SERVICE" python /app/datahub_scripts/import_data.py \
        --data-dir /app/data \
        --host "$PG_SERVICE" \
        --port 5432 \
        --user postgres \
        --password root \
        --db ruoyi-fastapi \
        --skip-large
    info "数据导入完成"
}

apply_data_asset_schema() {
    require_docker
    compose up -d "$PG_SERVICE"
    wait_pg_ready 90

    info "为现有数据库补齐 data_asset 新字段和索引，不重新导入数据"
    docker exec -i "$PG_SERVICE" psql -U postgres -d ruoyi-fastapi <<'SQL'
ALTER TABLE data_asset ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255) DEFAULT NULL;
ALTER TABLE data_asset ADD COLUMN IF NOT EXISTS storage_path TEXT DEFAULT NULL;
ALTER TABLE data_asset ADD COLUMN IF NOT EXISTS checksum VARCHAR(64) DEFAULT NULL;
ALTER TABLE data_asset ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'import';
ALTER TABLE data_asset ADD COLUMN IF NOT EXISTS upload_user_id BIGINT DEFAULT NULL;
ALTER TABLE data_asset ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_data_asset_source ON data_asset (source_type);
CREATE INDEX IF NOT EXISTS idx_data_asset_deleted ON data_asset (deleted_at);
CREATE INDEX IF NOT EXISTS idx_data_asset_checksum ON data_asset (checksum);
SQL
    info "data_asset 表结构补齐完成"
}

restart_services() {
    require_docker
    info "重启全部服务"
    compose restart
    show_status
}

stop_services() {
    require_docker
    info "停止全部服务，不删除 pgdata/redisdata/data_assets"
    compose stop
    show_status
}

show_logs() {
    require_docker
    local service="${1:-}"
    if [ -n "$service" ]; then
        compose logs -f "$service"
    else
        compose logs -f
    fi
}

reset_database() {
    require_docker
    echo ""
    warn "危险操作：这会停止服务并删除 $PROJECT_DIR/pgdata，数据库数据会丢失"
    warn "如果只是重新构建前后端，请不要选择这个操作"
    read -r -p "确认删除数据库？请输入 DELETE_PGDATA: " confirm
    if [ "$confirm" != "DELETE_PGDATA" ]; then
        warn "已取消数据库重置"
        return 0
    fi

    compose down
    rm -rf "$PROJECT_DIR/pgdata"
    mkdir -p "$PROJECT_DIR/pgdata"
    info "pgdata 已删除并重新创建"
    compose up -d "$PG_SERVICE" "$REDIS_SERVICE"
    wait_pg_ready 90
    warn "数据库已重置，如需农业数据请重新执行导入"
}

print_menu() {
    show_header
    cat <<'MENU'
请选择操作：

  1) 只重新构建前端
  2) 只重新构建后端
  3) 重新构建前端 + 后端
  4) 启动/重启数据库 + Redis（不删除数据）
  5) 启动全部服务（不重新构建）
  6) 完整部署（构建并启动全部，不导入数据）
  7) 导入农业数据（默认跳过大文件）
  8) 补齐 data_asset 表结构（不重新导入数据）
  9) 查看容器状态
 10) 查看全部日志
 11) 重启全部服务
 12) 停止全部服务（不删除数据）
 13) 危险：重置数据库 pgdata
  0) 退出

MENU
}

run_menu() {
    require_docker
    ensure_dirs
    while true; do
        print_menu
        read -r -p "输入编号: " choice
        case "$choice" in
            1) rebuild_frontend ;;
            2) rebuild_backend ;;
            3) rebuild_app ;;
            4) start_infra ;;
            5) start_all_no_build ;;
            6) full_deploy ;;
            7) import_data ;;
            8) apply_data_asset_schema ;;
            9) show_status ;;
            10) show_logs ;;
            11) restart_services ;;
            12) stop_services ;;
            13) reset_database ;;
            0) info "退出"; exit 0 ;;
            *) warn "无效选择: $choice" ;;
        esac
        echo ""
        read -r -p "按 Enter 返回菜单..." _
    done
}

case "${1:-menu}" in
    menu) run_menu ;;
    frontend) rebuild_frontend ;;
    backend) rebuild_backend ;;
    app) rebuild_app ;;
    infra) require_docker; start_infra ;;
    up) require_docker; start_all_no_build ;;
    full) full_deploy ;;
    import) import_data ;;
    migrate-assets) apply_data_asset_schema ;;
    status) require_docker; show_status ;;
    logs) require_docker; show_logs "${2:-}" ;;
    restart) restart_services ;;
    stop) stop_services ;;
    reset-db) reset_database ;;
    *)
        cat <<USAGE
用法:
  ./deploy.sh                  打开交互菜单
  ./deploy.sh frontend         只构建并启动前端
  ./deploy.sh backend          只构建并启动后端
  ./deploy.sh app              构建并启动前端 + 后端
  ./deploy.sh infra            启动数据库 + Redis，不删除数据
  ./deploy.sh up               启动全部服务，不构建
  ./deploy.sh full             构建并启动全部服务
  ./deploy.sh import           导入农业数据
  ./deploy.sh migrate-assets   补齐 data_asset 表结构
  ./deploy.sh status           查看容器状态
  ./deploy.sh logs [service]   查看日志
  ./deploy.sh restart          重启全部服务
  ./deploy.sh stop             停止全部服务，不删除数据
  ./deploy.sh reset-db         危险：删除 pgdata 并重建数据库

可选环境变量:
  PROJECT_DIR=/opt/neau-data-hub
  COMPOSE_FILE=docker-compose.pg.yml
USAGE
        exit 1
        ;;
esac
