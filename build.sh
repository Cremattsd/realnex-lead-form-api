#!/bin/bash

echo "Installing Flask & Gunicorn..."
pip install Flask gunicorn flask-cors

echo "Installing RealNex SDK from private GitHub..."
pip install "git+https://${GITHUB_TOKEN}@github.com/Cremattsd/realnex-sdk.git@main#egg=real_nex_sync_api_data_facade"

echo "Installation Complete!"
