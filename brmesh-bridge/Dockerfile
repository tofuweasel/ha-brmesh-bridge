ARG BUILD_FROM=ghcr.io/hassio-addons/base:16.3.2
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system requirements
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bluez \
    bluez-deprecated \
    gcc \
    g++ \
    musl-dev \
    linux-headers \
    git \
    openssh-client \
    ca-certificates \
    make \
    python3-dev

# Configure git for better compatibility
RUN git config --global http.postBuffer 524288000 && \
    git config --global http.lowSpeedLimit 0 && \
    git config --global http.lowSpeedTime 999999

# Download esphome-fastcon component to bundle with addon
RUN wget -O /tmp/fastcon.zip https://github.com/scross01/esphome-fastcon/archive/refs/heads/main.zip && \
    unzip /tmp/fastcon.zip -d /tmp && \
    mkdir -p /app/external_components && \
    mv /tmp/esphome-fastcon-main/components/fastcon /app/external_components/ && \
    rm -rf /tmp/fastcon.zip /tmp/esphome-fastcon-main

# Install Python packages
# Install ESPHome first to lock in its dependency versions (including paho-mqtt 1.6.1)
RUN pip3 install --break-system-packages --no-cache-dir \
    "esphome>=2024.11.0" \
    "platformio>=6.1.0"

# Install remaining packages (compatible with ESPHome's dependencies)
RUN pip3 install --break-system-packages --no-cache-dir \
    "bleak>=0.22.0,<1.0.0" \
    "flask>=3.0.0,<4.0.0" \
    "flask-cors>=5.0.0,<6.0.0" \
    "requests>=2.32.0,<3.0.0" \
    "pillow>=10.0.0,<12.0.0" \
    "numpy>=2.0.0,<3.0.0" \
    "ruamel.yaml>=0.17.0,<1.0.0"

# Pre-configure PlatformIO to use system Python and avoid creating venv
ENV PLATFORMIO_CORE_DIR=/config/.platformio
ENV PLATFORMIO_GLOBALLIB_DIR=/config/.platformio/lib
ENV PIO_INSTALL_DEVPLATFORM_SILENT=yes
ENV PLATFORMIO_NO_SYSTEM_SITEPACKAGES=false

# Initialize PlatformIO to cache platform files
RUN pio platform install espressif32@5.3.0 || true

# Copy addon files
COPY rootfs /

# Make service scripts executable
RUN chmod a+x /etc/services.d/brmesh-bridge/run /etc/services.d/brmesh-bridge/finish

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION

# Labels
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    maintainer="tofuweasel" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="Home Assistant Community Add-ons" \
    org.opencontainers.image.authors="tofuweasel" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.url="https://github.com/tofuweasel/ha-brmesh-bridge" \
    org.opencontainers.image.source="https://github.com/${BUILD_REPOSITORY}" \
    org.opencontainers.image.documentation="https://github.com/${BUILD_REPOSITORY}/blob/main/README.md" \
    org.opencontainers.image.created="${BUILD_DATE}" \
    org.opencontainers.image.revision="${BUILD_REF}" \
    org.opencontainers.image.version="${BUILD_VERSION}"
