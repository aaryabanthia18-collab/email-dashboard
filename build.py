#!/usr/bin/env python3
"""
Build script - Fetches emails and generates static dashboard HTML
"""

import json
import subprocess

# Run the update script to fetch emails
print("Fetching emails...")
subprocess.run(['python3', 'update_dashboard.py'])

# Read the data
with open('data.json', 'r') as f:
    data = f.read()

# Read the template
with open('index_template.html', 'r') as f:
    template = f.read()

# Replace placeholder with data
html = template.replace('DATA_PLACEHOLDER', data)

# Write the final HTML
with open('index.html', 'w') as f:
    f.write(html)

print("Dashboard built successfully!")
