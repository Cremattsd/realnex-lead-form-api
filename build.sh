#!/bin/bash
pip install Flask gunicorn
pip install "git+https://${GITHUB_TOKEN}@github.com/Cremattsd/realnex-sdk.git@main#egg=real_nex_sync_api_data_facade"
