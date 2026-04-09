#!/bin/bash
# Install dependencies
pip install -r requirements.txt

# Start the application using the $PORT environment variable
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
