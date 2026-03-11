#!/bin/bash
# IDCS Activation Helper
# Run this using: source ./activate_idcs.sh

echo "🚀 Activating IDCS Environment from Home Directory..."
source "/media/smilee/64 GB/new/myrepo/venv/bin/activate"
echo "✅ Environment Ready!"
python3 check_env.py
