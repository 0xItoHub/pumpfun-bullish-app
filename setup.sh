#!/usr/bin/env bash
# exit on error
set -o errexit

# Python version check
python --version

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt 