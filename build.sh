#!/bin/bash

echo "Installing Flask & Gunicorn..."
pip install Flask gunicorn flask-cors

echo "Installing SDK from PyPI/Zip via requirements.txt"
pip install -r requirements.txt
