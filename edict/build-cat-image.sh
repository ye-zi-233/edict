#!/usr/bin/env bash
# 在 feature/cat-kingdom 分支上构建并打 cat 相关 tag 的 Docker 镜像
# 用法：在仓库根目录执行  cd edict && ./build-cat-image.sh
# 或：  EDICT_IMAGE_TAG=cat-kingdom docker compose -f edict/docker-compose.yaml build

set -e
cd "$(dirname "$0")/.."
export EDICT_IMAGE_TAG="${EDICT_IMAGE_TAG:-cat-kingdom}"
echo "Building images with tag: $EDICT_IMAGE_TAG"
docker compose -f edict/docker-compose.yaml build
echo "Done. Images: edict-backend:$EDICT_IMAGE_TAG, edict-frontend:$EDICT_IMAGE_TAG"
echo "Push (if needed): docker push <registry>/edict-backend:$EDICT_IMAGE_TAG"
