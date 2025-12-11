#!/bin/sh
# Entrypoint customizado: opcionalmente sincroniza com um repositório Git e depois inicia o Nginx.
set -e

TARGET_DIR="/usr/share/nginx/html"
BRANCH="${REPO_BRANCH:-main}"

update_from_git(){
  if [ -d "$TARGET_DIR/.git" ]; then
    git -C "$TARGET_DIR" fetch --depth=1 origin "$BRANCH" || return 1
    git -C "$TARGET_DIR" reset --hard "origin/$BRANCH" || return 1
  else
    tmpdir="$(mktemp -d)"
    git clone --depth=1 --branch "$BRANCH" "$REPO_URL" "$tmpdir" || return 1
    rsync -a --delete "$tmpdir"/ "$TARGET_DIR"/ || return 1
    rm -rf "$tmpdir"
  fi
}

if [ "${AUTO_UPDATE:-true}" != "false" ] && [ -n "$REPO_URL" ]; then
  echo "[entrypoint] Atualizando a partir de $REPO_URL (branch: $BRANCH)..."
  update_from_git || echo "[entrypoint] Aviso: não foi possível atualizar; usando arquivos atuais."
else
  echo "[entrypoint] AUTO_UPDATE desativado ou REPO_URL vazio; seguindo com arquivos atuais."
fi

exec /docker-entrypoint.sh nginx -g 'daemon off;'
