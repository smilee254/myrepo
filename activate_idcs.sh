#!/bin/bash
# IDCS Activation Helper
# Run this using: source ./activate_idcs.sh

echo "🚀 Activating IDCS Environment from Home Directory..."
source ~/idcs_venv/bin/activate
echo "✅ Environment Ready!"
python3 check_env.py
