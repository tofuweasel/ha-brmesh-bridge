#!/usr/bin/with-contenv bashio

CONFIG_PATH=/data/options.json

export MESH_KEY=$(bashio::config 'mesh_key')
export MQTT_HOST=$(bashio::config 'mqtt_host')
export MQTT_PORT=$(bashio::config 'mqtt_port')
export MQTT_USER=$(bashio::config 'mqtt_user')
export MQTT_PASSWORD=$(bashio::config 'mqtt_password')
export DISCOVERY_ENABLED=$(bashio::config 'discovery_enabled')

bashio::log.info "Starting BRMesh Bridge..."
bashio::log.info "Mesh Key: ${MESH_KEY}"
bashio::log.info "MQTT: ${MQTT_HOST}:${MQTT_PORT}"

python3 /brmesh_bridge.py
