# 构建阶段
FROM node:18-slim AS builder
WORKDIR /app

# 设置npm镜像源
RUN npm config set registry https://registry.npmmirror.com

# 先单独拷贝 package 文件（利用 Docker 层缓存，依赖不变则这层 CACHED）
# 关键：分两次 COPY，避免 BuildKit cache key 计算时对多文件做联合 snapshot
#       （Docker 25/26 在某些 storage driver 下，联合 snapshot 会假报 "not found"）
COPY package.json ./
COPY package-lock.json ./

# 安装依赖
#  --no-audit --no-fund：跳过安全审计和资金提示，国内镜像源更稳
#  --prefer-offline：本地有缓存就用，buildx cache 也能命中
RUN npm ci --no-audit --no-fund --prefer-offline \
    || npm install --no-audit --no-fund --prefer-offline --no-save

# 增大 Node.js 内存限制，防止构建 OOM
ENV NODE_OPTIONS="--max-old-space-size=1536"

# 再拷贝其余源码（node_modules 已经在上一层装好了）
# 关键：用 .dockerignore 排除 node_modules / dist / 日志 / .env.* 等
COPY . .

# 执行docker构建命令
RUN npm run build:docker

# 运行阶段
FROM nginx:latest
WORKDIR /usr/share/nginx/html

# 复制构建产物
COPY --from=builder /app/dist .

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]