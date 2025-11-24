#!/usr/bin/with-contenv bashio

bashio::log.info "Starting BRMesh Bridge..."
bashio::log.info "Zero-config start - configure via Web UI"

python3 /brmesh_bridge.py
