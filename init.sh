#!/usr/bin/env bash
# init.sh — prepara el entorno y verifica que la suite pasa.
# Idempotente. Debe terminar en exit 0 para considerar el entorno sano.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "==> wow-classic-rag :: init"

# 1. Python disponible
PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY="python"
fi
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: no se encontró python3/python en PATH." >&2
  exit 1
fi
echo "==> Python: $("$PY" --version 2>&1)"

# 2. Entorno virtual
if [ ! -d ".venv" ]; then
  echo "==> Creando .venv"
  "$PY" -m venv .venv
fi
# Activación multiplataforma (Linux/macOS vs Git-Bash en Windows)
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
elif [ -f ".venv/Scripts/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/Scripts/activate"
fi

# 3. Dependencias (si ya existe requirements.txt; lo crea la feature f0)
if [ -f "requirements.txt" ] && [ -s "requirements.txt" ]; then
  echo "==> Instalando dependencias"
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet -r requirements.txt
else
  echo "==> (sin requirements.txt todavía; se creará en f0-project-skeleton)"
fi

# 4. Tests (excluye integración con servicios reales)
if python -c "import pytest" >/dev/null 2>&1; then
  if find tests -name 'test_*.py' -type f 2>/dev/null | grep -q .; then
    echo "==> Ejecutando pytest (no integration)"
    pytest -q -m "not integration"
  else
    echo "==> (aún no hay tests; se añadirán al implementar features)"
  fi
else
  echo "==> (pytest no instalado todavía; se instalará con requirements.txt)"
fi

echo "==> init OK"
