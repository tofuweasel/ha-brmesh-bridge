ARG BUILD_FROM=ghcr.io/hassio-addons/base:16.3.2
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install requirements
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bluez \
    bluez-deprecated

# Install Python packages (latest stable versions)
RUN pip3 install --break-system-packages --no-cache-dir \
    "paho-mqtt>=2.0.0,<3.0.0" \
    "bleak>=0.22.0,<1.0.0" \
    "pyyaml>=6.0.0,<7.0.0" \
    "flask>=3.0.0,<4.0.0" \
    "flask-cors>=5.0.0,<6.0.0" \
    "requests>=2.32.0,<3.0.0" \
    "pillow>=10.0.0,<12.0.0" \
    "numpy>=2.0.0,<3.0.0"

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
