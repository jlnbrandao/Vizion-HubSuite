#!/usr/bin/env bash
# Publica este repo em ssh vizion-g:/opt/vizion-h-suite
#
# Uso (na máquina local, na raiz do repo):
#   ./deploy/scripts/remote-deploy.sh            # sync + build + restart
#   ./deploy/scripts/remote-deploy.sh --sync     # só rsync
#   ./deploy/scripts/remote-deploy.sh --bootstrap  # 1ª vez: Python 3.13, DB, systemd, nginx
#
# Variáveis: DEPLOY_HOST (default vizion-g)  DEPLOY_DIR (default /opt/vizion-h-suite)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${DEPLOY_HOST:-vizion-g}"
DIR="${DEPLOY_DIR:-/opt/vizion-h-suite}"
MODE="deploy"

for arg in "$@"; do
  case "$arg" in
    --sync) MODE="sync" ;;
    --bootstrap) MODE="bootstrap" ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "Opção desconhecida: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${ROOT}/deploy/rsync-exclude.txt" ]]; then
  echo "Execute a partir do clone do vizion-h-suite." >&2
  exit 1
fi

echo "==> Destino ${HOST}:${DIR}  (modo=${MODE})"
ssh "${HOST}" "mkdir -p '${DIR}'"

echo "==> enviando árvore"
if command -v rsync >/dev/null 2>&1; then
  rsync -az --delete \
    --exclude-from="${ROOT}/deploy/rsync-exclude.txt" \
    "${ROOT}/" "${HOST}:${DIR}/"
else
  echo "    (rsync ausente nesta máquina — tar+ssh; instale rsync para --delete)"
  tar -C "${ROOT}" \
    --exclude=.git \
    --exclude=.venv \
    --exclude=node_modules \
    --exclude=__pycache__ \
    --exclude=.pytest_cache \
    --exclude=.mypy_cache \
    --exclude=.ruff_cache \
    --exclude=.coverage \
    --exclude=htmlcov \
    --exclude=.DS_Store \
    --exclude=temp \
    --exclude=.cursor \
    --exclude=.vscode \
    --exclude=backend/.env \
    --exclude=frontend/dist \
    --exclude='*.egg-info' \
    -cf - . | ssh "${HOST}" "tar -C '${DIR}' --overwrite -xf -"
fi

if [[ "${MODE}" == "sync" ]]; then
  echo "Sync ok. ${HOST}:${DIR}"
  exit 0
fi

ssh "${HOST}" "MODE='${MODE}' DIR='${DIR}' bash -s" <<'REMOTE'
set -euo pipefail
cd "${DIR}"

need_python() {
  if [[ -x "${DIR}/backend/.venv/bin/python" ]]; then
    "${DIR}/backend/.venv/bin/python" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)'
    return
  fi
  return 1
}

ensure_uv_python() {
  if need_python; then
    return
  fi
  if ! command -v uv >/dev/null 2>&1; then
    echo "==> Instalando uv (Python 3.13)"
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
    export PATH="/usr/local/bin:${PATH}"
  fi
  echo "==> Criando venv 3.13"
  uv python install 3.13
  uv venv "${DIR}/backend/.venv" --python 3.13
}

if [[ "${MODE}" == "bootstrap" ]]; then
  ensure_uv_python

  if [[ ! -f "${DIR}/backend/.env" ]]; then
    echo "==> Gerando backend/.env (produção HTTP :8088)"
    JWT="$(openssl rand -hex 32)"
    DB_OWNER_PW="$(openssl rand -hex 16)"
    DB_APP_PW="$(openssl rand -hex 16)"
    SERVER_IP="$(hostname -I | awk '{print $1}')"
    cat > "${DIR}/backend/.env" <<EOF
APP_NAME=Vizion
APP_ENV=production
APP_DEBUG=false
APP_HOST=127.0.0.1
APP_PORT=8010

DATABASE_URL=postgresql+asyncpg://vizion_app:${DB_APP_PW}@127.0.0.1:5432/vizion_hub_prod
DATABASE_MIGRATE_URL=postgresql+asyncpg://vizion:${DB_OWNER_PW}@127.0.0.1:5432/vizion_hub_prod
REDIS_URL=redis://127.0.0.1:6379/1

JWT_SECRET_KEY=${JWT}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
COOKIE_SECURE=true
HSTS_ENABLED=false

ALLOWED_TENANT_BASE_DOMAINS=localhost,openvizion.com,openvizion.local
TENANT_SLUG_ALIASES=lanstar:universe

HUB_ENVIRONMENT=vps
HUB_PUBLIC_HOST=universe.openvizion.com
HUB_PUBLIC_API_PORT=443
HUB_PUBLIC_UI_PORT=443
HUB_NOTES="HubSuite on vizion-g. Lanstar UI proxied at lanstar.openvizion.com"

LANSTAR_PUBLIC_HOST=lanstar.openvizion.com
LANSTAR_ORIGIN_HOST=134.209.122.250
LANSTAR_ORIGIN_PORT=80
EOF
    chmod 600 "${DIR}/backend/.env"

    echo "==> Criando roles/database Postgres (se ainda não existirem)"
    sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vizion') THEN
    CREATE ROLE vizion LOGIN PASSWORD '${DB_OWNER_PW}';
  ELSE
    ALTER ROLE vizion PASSWORD '${DB_OWNER_PW}';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vizion_app') THEN
    CREATE ROLE vizion_app LOGIN PASSWORD '${DB_APP_PW}';
  ELSE
    ALTER ROLE vizion_app PASSWORD '${DB_APP_PW}';
  END IF;
END
\$\$;
SQL
    if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='vizion_hub_prod'" | grep -q 1; then
      sudo -u postgres createdb -O vizion vizion_hub_prod
    fi
    sudo -u postgres psql -d vizion_hub_prod -v ON_ERROR_STOP=1 -c "GRANT CONNECT ON DATABASE vizion_hub_prod TO vizion_app;"
  fi

  # 0009 cria vizion_migrate via CREATE ROLE; o owner `vizion` não tem CREATEROLE.
  echo "==> Garantindo role vizion_migrate (Alembic 0009)"
  sudo -u postgres psql -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'vizion_migrate') THEN
    CREATE ROLE vizion_migrate LOGIN PASSWORD 'vizion_migrate' NOSUPERUSER BYPASSRLS;
  END IF;
END
$$;
SQL
fi

if [[ ! -x "${DIR}/backend/.venv/bin/python" ]]; then
  echo "ERRO: venv 3.13 ausente. Rode: ./deploy/scripts/remote-deploy.sh --bootstrap" >&2
  exit 1
fi

echo "==> Dependências da API"
(
  cd "${DIR}/backend"
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python .venv/bin/python -e .
  else
    .venv/bin/pip install -e .
  fi
)

echo "==> Migrações"
(
  cd "${DIR}/backend"
  .venv/bin/alembic upgrade head
)
# SECURITY DEFINER + FORCE RLS: só o superuser consegue SET app.rls_bypass na função.
sudo -u postgres psql -d vizion_hub_prod -v ON_ERROR_STOP=1 \
  -c "ALTER FUNCTION resolve_tenant_by_slug(text) SET app.rls_bypass = 'on'"

echo "==> Frontend"
(
  cd "${DIR}/frontend"
  npm ci
  npm run build
)

echo "==> nginx (HubSuite universe/ows + proxy lanstar)"
install -m 644 "${DIR}/deploy/nginx/vizion-h.conf" /etc/nginx/sites-available/vizion-h.conf
ln -sfn /etc/nginx/sites-available/vizion-h.conf /etc/nginx/sites-enabled/vizion-h.conf
install -m 644 "${DIR}/deploy/nginx/lanstar.openvizion.com.conf" \
  /etc/nginx/sites-available/lanstar.openvizion.com
ln -sfn /etc/nginx/sites-available/lanstar.openvizion.com \
  /etc/nginx/sites-enabled/lanstar.openvizion.com
nginx -t
systemctl reload nginx

if [[ "${MODE}" == "bootstrap" ]]; then
  echo "==> systemd vizion-h-api"
  install -m 644 "${DIR}/deploy/systemd/vizion-h-api.service" /etc/systemd/system/vizion-h-api.service
  systemctl daemon-reload
  systemctl enable vizion-h-api.service
fi

if systemctl list-unit-files vizion-h-api.service >/dev/null 2>&1 \
   && systemctl cat vizion-h-api.service >/dev/null 2>&1; then
  echo "==> restart vizion-h-api"
  systemctl restart vizion-h-api.service
  systemctl --no-pager --full status vizion-h-api.service | sed -n '1,20p' || true
else
  echo "Serviço ainda não instalado. Primeira vez: ./deploy/scripts/remote-deploy.sh --bootstrap"
fi

echo
echo "Pronto. UI: http://$(hostname -I | awk '{print $1}'):8088/"
echo "Health: http://127.0.0.1:8010/health"
REMOTE
