#!/usr/bin/env bash
# Instala NGINX + systemd para manter o Lanstar sempre online.
# Uso: sudo bash /opt/lanstar/deploy/scripts/install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEPLOY="${ROOT}/deploy"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Execute como root: sudo bash $0" >&2
  exit 1
fi

echo "==> Instalando nginx (se necessário)"
if ! command -v nginx >/dev/null 2>&1; then
  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y nginx
fi

echo "==> Verificando frontend build"
if [[ ! -f "${ROOT}/frontend/dist/index.html" ]]; then
  echo "    dist/ ausente — fazendo build..."
  (cd "${ROOT}/frontend" && npm ci && npm run build)
fi

echo "==> Verificando venv da API"
if [[ ! -x "${ROOT}/backend/.venv/bin/uvicorn" ]]; then
  echo "ERRO: ${ROOT}/backend/.venv/bin/uvicorn não encontrado." >&2
  echo "Crie o venv e instale: cd backend && python -m venv .venv && .venv/bin/pip install -e ." >&2
  exit 1
fi

if [[ ! -f "${ROOT}/backend/.env" ]]; then
  echo "==> Copiando .env.example → .env"
  cp "${ROOT}/backend/.env.example" "${ROOT}/backend/.env"
fi

echo "==> Configurando nginx"
# Remover default que conflita com listen 80
rm -f /etc/nginx/sites-enabled/default
install -m 644 "${DEPLOY}/nginx/lanstar.conf" /etc/nginx/sites-available/lanstar.conf
ln -sfn /etc/nginx/sites-available/lanstar.conf /etc/nginx/sites-enabled/lanstar.conf
nginx -t
systemctl reload nginx 2>/dev/null || systemctl restart nginx

echo "==> Instalando units systemd"
install -m 644 "${DEPLOY}/systemd/lanstar-infra.service" /etc/systemd/system/lanstar-infra.service
install -m 644 "${DEPLOY}/systemd/lanstar-api.service" /etc/systemd/system/lanstar-api.service
install -m 644 "${DEPLOY}/systemd/lanstar.target" /etc/systemd/system/lanstar.target
systemctl daemon-reload

echo "==> Parando containers Docker da API/frontend (evita conflito de porta)"
(cd "${ROOT}" && docker compose stop api frontend 2>/dev/null || true)

echo "==> Habilitando e iniciando serviços"
systemctl enable --now lanstar-infra.service
systemctl enable --now lanstar-api.service
systemctl enable --now nginx.service
systemctl enable lanstar.target

echo "==> Aguardando health da API"
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "    API OK"
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    echo "AVISO: API ainda não respondeu em /health — verifique: journalctl -u lanstar-api -n 50" >&2
  fi
  sleep 1
done

echo
echo "Status:"
systemctl --no-pager --full status lanstar-infra.service lanstar-api.service nginx.service | sed -n '1,80p' || true
echo
echo "Pronto. App: http://$(hostname -I | awk '{print $1}')/"
echo "Comandos úteis:"
echo "  systemctl status lanstar-api"
echo "  systemctl restart lanstar-api"
echo "  journalctl -u lanstar-api -f"
echo "  systemctl start lanstar.target"
