#!/usr/bin/env bash
# Exit on error
set -e

# Step 1: Install system dependencies (Java)
echo "---> Installing Java JRE..."
apt-get update && apt-get install -y default-jre

# Step 2: Install Python dependencies
echo "---> Installing Python requirements..."
pip install -r requirements.txt
