import os
import socket
from dotenv import load_dotenv

load_dotenv()

# Server Settings
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Pod / Container Hostname for observability and load balancing verification
POD_NAME = os.getenv("HOSTNAME") or os.getenv("POD_NAME") or socket.gethostname()

# MongoDB Settings
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017/notifications_db"
)
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "notifications_db")

# RabbitMQ Settings (Supports both RABBITMQ_HOST and full RABBITMQ_URL)
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

# Default connection URL derived from RABBITMQ_HOST or explicit RABBITMQ_URL
_DEFAULT_RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
RABBITMQ_URL = os.getenv("RABBITMQ_URL", _DEFAULT_RABBITMQ_URL)

RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "app_events_exchange")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "pedidos_events")
RABBITMQ_ROUTING_KEYS = [
    rk.strip()
    for rk in os.getenv("RABBITMQ_ROUTING_KEYS", "pedidos_events,order.*,user.*,#").split(",")
    if rk.strip()
]
