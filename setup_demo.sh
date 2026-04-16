#!/bin/bash
# This script copies demo_data.json to the frontend folder so the app works
# when opened directly (without the FastAPI backend running)
cp data/demo_data.json frontend/demo_data.json
echo "Demo data copied to frontend/ ✓"
