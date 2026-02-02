# Multi-arch base image
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Install dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash

# Set working directory
WORKDIR /app

# Install Python packages
COPY requirements.txt ./
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Copy application
COPY modbus_energy_meter ./modbus_energy_meter/
COPY run.sh /
RUN chmod a+x /run.sh

# Labels
LABEL \
    io.hass.name="huABus | Huawei Solar Modbus to MQTT" \
    io.hass.description="Huawei Solar Modbus → MQTT + Auto-Discovery" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64|armhf|armv7|i386"

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "python3.*modbus_energy_meter.main" > /dev/null || exit 1

# Start
CMD ["/run.sh"]
