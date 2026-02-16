#!/bin/bash
# Build script - Fetches emails and generates static dashboard

cd /root/.openclaw/workspace/email-dashboard

# Fetch emails and generate data.json
python3 update_dashboard.py

# Read the data
DATA=$(cat data.json)

# Replace placeholder in template with actual data
sed "s|DATA_PLACEHOLDER|$DATA|g" index_template.html > index.html

echo "Dashboard built successfully at $(date)"
