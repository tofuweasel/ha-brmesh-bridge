ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bluez \
    bluez-deprecated \
    nginx

# Install Python packages
RUN pip3 install --no-cache-dir \
    paho-mqtt \
    bleak \
    pyyaml \
    flask \
    flask-cors \
    requests \
    pillow \
    numpy

# Copy addon files
COPY run.sh /
COPY brmesh_bridge.py /
COPY effects.py /
COPY web_ui.py /
COPY esphome_generator.py /
COPY ble_discovery.py /
COPY app_importer.py /
COPY nspanel_ui.py /
COPY static /static
COPY templates /templates

RUN chmod a+x /run.sh

EXPOSE 8099

CMD [ "/run.sh" ]
