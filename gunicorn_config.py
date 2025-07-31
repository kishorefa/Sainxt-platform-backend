# Gunicorn configuration
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:${PORT:-10000}"
timeout = 120
keepalive = 5
threads = 4
worker_connections = 1000
