import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import config
from app.database import (
    check_db_health,
    list_notifications,
    get_notifications_by_user,
)
from app.consumer import (
    start_consumer_thread,
    stop_consumer_thread,
    check_rabbitmq_health,
    publish_event,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("ms-notifications")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch RabbitMQ background consumer thread without blocking HTTP API
    logger.info("Starting up ms-notifications on pod/host: %s", config.POD_NAME)
    start_consumer_thread()
    yield
    # Shutdown: Signal consumer thread to exit cleanly
    logger.info("Shutting down ms-notifications...")
    stop_consumer_thread()


app = FastAPI(
    title="ms-notifications",
    description="Microsserviço de Notificações e Auditoria (Cloud Native / EKS)",
    version="1.0.0",
    lifespan=lifespan,
)


class TestOrderEvent(BaseModel):
    order_id: Optional[str] = Field(default=None, description="ID do pedido")
    event_id: Optional[str] = Field(default=None, description="ID do evento")
    event_type: Optional[str] = Field(default="PEDIDO_CRIADO", description="Tipo de evento")
    user_id: Optional[str] = Field(default="user_123", description="ID do cliente/usuário")
    payload: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {"total": 199.90, "itens": 2},
        description="Dados do pedido",
    )


def build_health_response():
    db_ok = check_db_health()
    rmq_ok = check_rabbitmq_health()
    is_up = db_ok and rmq_ok

    content = {
        "status": "ok" if is_up else "degraded",
        "pod": config.POD_NAME,
        "db": "connected" if db_ok else "disconnected",
        "rabbitmq": "connected" if rmq_ok else "disconnected",
    }
    status_code = status.HTTP_200_OK if is_up else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=content)


# --- Endpoints REST ---

@app.get("/", tags=["Root"])
def root_redirect():
    """Retorna listagem padrão para compatibilidade com rewrite-target."""
    return get_notifications(limit=50, skip=0)


@app.get("/health", tags=["Health"])
@app.get("/api/notifications/health", tags=["Health"])
def get_health():
    """
    Endpoint de verificação de saúde (GET /health).
    Retorna {"status": "ok", "pod": "<HOSTNAME>", ...}
    """
    return build_health_response()


@app.get("/notifications", tags=["Notifications"])
@app.get("/api/notifications", tags=["Notifications"])
def get_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
):
    """
    Retorna a listagem dos eventos recebidos e gravados no MongoDB.
    """
    try:
        notifications = list_notifications(limit=limit, skip=skip)
        return {
            "status": "ok",
            "pod": config.POD_NAME,
            "count": len(notifications),
            "limit": limit,
            "skip": skip,
            "items": notifications,
        }
    except Exception as exc:
        logger.error("Failed to list notifications: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar notificações: {str(exc)}",
        )


@app.get("/notifications/user/{user_id}", tags=["Notifications"])
@app.get("/api/notifications/user/{user_id}", tags=["Notifications"])
def get_user_notifications(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Retorna as notificações de um usuário específico.
    """
    try:
        notifications = get_notifications_by_user(user_id=user_id, limit=limit)
        return {
            "status": "ok",
            "pod": config.POD_NAME,
            "user_id": user_id,
            "count": len(notifications),
            "items": notifications,
        }
    except Exception as exc:
        logger.error("Failed to query notifications for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar notificações do usuário: {str(exc)}",
        )


@app.post("/notifications/test", tags=["Testing"])
@app.post("/api/notifications/test", tags=["Testing"])
def post_test_notification(body: Optional[TestOrderEvent] = None):
    """
    Publica um evento de teste na fila pedidos_events para validação do fluxo end-to-end.
    """
    data = body or TestOrderEvent()
    order_id = data.order_id or f"ped-{uuid.uuid4().hex[:8]}"
    event_id = data.event_id or f"evt-{uuid.uuid4()}"

    event_dict = {
        "order_id": order_id,
        "event_id": event_id,
        "event_type": data.event_type or "PEDIDO_CRIADO",
        "user_id": data.user_id or "user_123",
        "payload": data.payload or {"total": 199.90, "itens": 2},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        publish_event(event_dict, routing_key=config.RABBITMQ_QUEUE)
        return {
            "status": "published",
            "pod": config.POD_NAME,
            "queue": config.RABBITMQ_QUEUE,
            "message": "Evento publicado na fila com sucesso. O worker processará em segundo plano.",
            "event": event_dict,
        }
    except Exception as exc:
        logger.error("Failed to publish test event: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao publicar evento no RabbitMQ: {str(exc)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload=False)
