ARG BUILD_FROM=ghcr.io/hassio-addons/base:16.3.2
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install requirements
RUN apk add --no-cache \
    python3=3.12.7-r1 \
    py3-pip=24.3.1-r0 \
    bluez=5.78-r1 \
    bluez-deprecated=5.78-r1

# Install Python packages
RUN pip3 install --break-system-packages --no-cache-dir \
    paho-mqtt==2.1.0 \
    bleak==0.22.3 \
    pyyaml==6.0.2 \
    flask==3.0.3 \
    flask-cors==5.0.0 \
    requests==2.32.3 \
    pillow==11.0.0 \
    numpy==2.1.3

# Copy addon files
COPY rootfs /

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
