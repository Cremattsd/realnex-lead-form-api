#!/bin/bash

echo "Installing Flask & Gunicorn..."
pip install Flask gunicorn flask-cors

echo "Installing RealNex SDK from GitHub..."
pip install "git+https://github.com/Cremattsd/realnex-sdk.git@main#egg=real_nex_sync_api_data_facade&subdirectory=src/real_nex_sync_api_data_facade"
