#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SERVICE_NAME="robotcar"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SERVICE_USER="${ROBOTCAR_USER:-${SUDO_USER:-}}"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script with sudo, for example: sudo ./deploy.sh" >&2
    exit 1
fi

if [[ -z "${SERVICE_USER}" || "${SERVICE_USER}" == "root" ]] ||
    ! getent passwd "${SERVICE_USER}" >/dev/null; then
    echo "Could not determine a non-root service user." >&2
    echo "Run with sudo from your normal account, or set ROBOTCAR_USER." >&2
    exit 1
fi

if [[ ! -f "${APP_DIR}/app.py" || ! -d "${APP_DIR}/templates" ]]; then
    echo "Expected app.py and templates/ in ${APP_DIR}." >&2
    exit 1
fi

if ! command -v apt-get >/dev/null; then
    echo "This installer requires Raspberry Pi OS or another apt-based system." >&2
    exit 1
fi

echo "Installing Robot Car system dependencies..."
apt-get update
apt-get install -y \
    python3-flask \
    python3-opencv \
    python3-picamera2 \
    python3-rpi.gpio

supplementary_groups=()
for group in gpio video; do
    if getent group "${group}" >/dev/null; then
        usermod -aG "${group}" "${SERVICE_USER}"
        supplementary_groups+=("${group}")
    fi
done

groups_line=""
if (("${#supplementary_groups[@]}" > 0)); then
    groups_line="SupplementaryGroups=${supplementary_groups[*]}"
fi

cat >"${SERVICE_FILE}" <<EOF
[Unit]
Description=Robot Car Web App
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/python3 ${APP_DIR}/app.py
Restart=on-failure
RestartSec=3
KillSignal=SIGINT
TimeoutStopSec=10
Environment=PYTHONUNBUFFERED=1
${groups_line}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo
echo "Robot Car service installed and started."
echo "Open http://<raspberry-pi-ip>:5000 from a device on the same network."
echo "Check status with: sudo systemctl status ${SERVICE_NAME}"
