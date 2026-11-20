#!/usr/bin/env bash
# ==============================================================================
# ONYX Portable Personal AI — Automated VPS Setup Script
# Target OS: Ubuntu 22.04 / 24.04 LTS (x86_64 or aarch64)
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo " Starting ONYX VPS Bootstrap Installation"
echo "=========================================================="

# 1. Update and install base packages
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    libpq-dev

# 2. Setup project directory
INSTALL_DIR="/opt/onyx"
sudo mkdir -p "${INSTALL_DIR}"
sudo chown -R "${USER}:${USER}" "${INSTALL_DIR}"

# 3. Create Python virtual environment
cd "${INSTALL_DIR}"
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in ${INSTALL_DIR}/.venv..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip setuptools wheel

# 4. Install ONYX dependencies
if [ -f "pyproject.toml" ]; then
    echo "Installing ONYX in editable mode..."
    pip install -e .
fi

# 5. Run ONYX setup
echo "Running 'onyx setup'..."
"${INSTALL_DIR}/.venv/bin/onyx" setup

# 6. Optional: Create systemd service
SERVICE_FILE="/etc/systemd/system/onyx.service"
if [ ! -f "${SERVICE_FILE}" ]; then
    echo "Creating systemd service: ${SERVICE_FILE}..."
    sudo bash -c "cat <<EOF > ${SERVICE_FILE}
[Unit]
Description=ONYX Portable Personal AI Service
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/.venv/bin/onyx start --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5
Environment=ONYX_ENV=production

[Install]
WantedBy=multi-user.target
EOF"
    sudo systemctl daemon-reload
    sudo systemctl enable onyx
    echo "ONYX systemd service enabled. Start with: sudo systemctl start onyx"
fi

echo "=========================================================="
echo " ONYX VPS Installation Complete!"
echo " Web Console: http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP'):8080"
echo "=========================================================="
