#!/bin/bash
# CAI Application startup script — runs Qdrant vector database
# CDSW/CAI apps should listen on port 8090 (proxied to your subdomain)

set -euo pipefail

QDRANT_VERSION="v1.11.3"
INSTALL_DIR="${HOME}/qdrant"
DATA_DIR="${HOME}/qdrant_storage"
mkdir -p "${INSTALL_DIR}" "${DATA_DIR}"

if [[ ! -x "${INSTALL_DIR}/qdrant" ]]; then
  echo "Downloading Qdrant ${QDRANT_VERSION}..."
  cd "${INSTALL_DIR}"
  curl -fsSL \
    "https://github.com/qdrant/qdrant/releases/download/${QDRANT_VERSION}/qdrant-x86_64-unknown-linux-musl.tar.gz" \
    -o qdrant.tar.gz
  tar -xzf qdrant.tar.gz
  chmod +x qdrant
fi

# CAI Application proxy expects port 8090
export QDRANT__SERVICE__HTTP_PORT=8090
export QDRANT__SERVICE__GRPC_PORT=6334
export QDRANT__STORAGE__STORAGE_PATH="${DATA_DIR}"

echo "Starting Qdrant on port 8090..."
echo "Data path: ${DATA_DIR}"
exec "${INSTALL_DIR}/qdrant"
