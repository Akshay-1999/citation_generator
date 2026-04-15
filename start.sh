#!/bin/bash
# Start the FastAPI application using Gunicorn with Uvicorn workers
# We use 2 workers for the Render Free tier to balance performance and memory limits.
gunicorn app:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
