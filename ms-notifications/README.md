# ms-notifications: Microsserviço de Notificações e Auditoria

Microsserviço Cloud-Native de alta performance e baixo consumo de recursos (**FastAPI + MongoDB + RabbitMQ**), desenvolvido para ambientes com restrição de CPU/Memória (como instâncias `t3.medium` do **AWS Academy / Amazon EKS**).

---

## 1. Limpeza Prévia de Recursos Docker

Antes de iniciar containers na sua máquina host, execute os comandos de limpeza para liberar memória, portas e disco:

### No Windows (PowerShell):
```powershell
docker ps -aq | ForEach-Object { docker stop $_; docker rm $_ }
docker volume prune -f
docker network prune -f
docker image prune -f
```

### No Linux / macOS / Git Bash:
```bash
docker stop $(docker ps -aq) 2>/dev/null || true
docker rm $(docker ps -aq) 2>/dev/null || true
docker network prune -f
docker volume prune -f
docker image prune -f
```

---

## 2. Executando Localmente com Docker Compose

O arquivo `docker-compose.yml` sobe o ambiente completo com App, MongoDB e RabbitMQ (com fila `pedidos_events`).

### Iniciar os serviços:
```bash
cd ms-notifications
docker compose up --build -d
```

### Verificar status dos containers:
```bash
docker compose ps
```

### Acessar a aplicação e ferramentas:
* **API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
* **Painel RabbitMQ:** [http://localhost:15672](http://localhost:15672) (usuário: `guest` / senha: `guest`)

---

## 3. Testando os Fluxos da Aplicação

### 3.1 Verificar Saúde dos Serviços (GET /health)
```bash
curl -X GET http://localhost:8000/health
```
**Resposta esperada (HTTP 200):**
```json
{
  "status": "ok",
  "pod": "ms-notifications-app",
  "db": "connected",
  "rabbitmq": "connected"
}
```

### 3.2 Publicar Evento de Teste na Fila pedidos_events
```bash
curl -X POST http://localhost:8000/notifications/test \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ped-102938",
    "event_type": "PEDIDO_CRIADO",
    "user_id": "user_pucpr_01",
    "payload": {
      "total": 249.90,
      "itens": 3
    }
  }'
```

### 3.3 Acompanhar o Consumidor nos Logs
Veja a mensagem sendo consumida com o formato acadêmico obrigatório para comprovação de balanceamento:
```bash
docker compose logs -f app
```
**Saída registrada no console:**
```text
[ms-notifications-app] Mensagem recebida e gravada: ped-102938
```

### 3.4 Consultar Histórico Persistido no MongoDB
```bash
# Listar todas as notificações
curl -X GET http://localhost:8000/notifications

# Filtrar por usuário
curl -X GET http://localhost:8000/notifications/user/user_pucpr_01
```

---

## 4. Deploy no Amazon EKS (Kubernetes)

### 4.1 Criar o Cluster com eksctl (AWS Academy)
Configure o ARN das roles em `aws/eks-cluster-academy.yaml` e execute:
```bash
eksctl create cluster -f aws/eks-cluster-academy.yaml
```

### 4.2 Preparar e Enviar a Imagem Docker (Amazon ECR)
Substitua `<ACCOUNT_ID>` conforme sua conta AWS Academy:
```bash
# 1. Login no ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# 2. Build e Tag da imagem
docker build -t ms-notifications:latest .
docker tag ms-notifications:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ms-notifications:latest

# 3. Push para o repositório ECR
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ms-notifications:latest
```

### 4.3 Aplicar Manifestos no Cluster EKS
```bash
kubectl apply -f k8s/
```

---

## 5. Roteiro de Demonstração para a Apresentação em Sala (10,0 Pontos)

Para a arguição prática de 3 minutos com o professor:

1. **Demonstrar os Pods rodando:**
   ```bash
   kubectl get pods -l app=ms-notifications
   ```
   *Mostre os 3 Pods ativos com status `Running` (Requisitos 4 e 9).*

2. **Demonstrar o isolamento de persistência:**
   ```bash
   kubectl get svc mongo-notification-service
   ```
   *Explique que este banco pertence unicamente a este serviço (Requisito 5).*

3. **Demonstrar o consumo assíncrono e balanceamento de carga:**
   Abra a visualização de logs das réplicas em tempo real:
   ```bash
   kubectl logs -l app=ms-notifications -f --prefix=true
   ```
   *Peça para o colega do MS-A disparar 3 pedidos seguidos via Postman (ou use o endpoint `/notifications/test`).*
   *Aponte para a tela mostrando que cada Pod diferente consumiu uma mensagem da fila:*
   `[ms-notifications-deployment-xxxx-1] Mensagem recebida e gravada: ped-1`
   `[ms-notifications-deployment-xxxx-2] Mensagem recebida e gravada: ped-2`
   `[ms-notifications-deployment-xxxx-3] Mensagem recebida e gravada: ped-3`

4. **Demonstrar a leitura via Ingress NGINX:**
   Abra o navegador ou o Postman na URL do Load Balancer AWS:
   ```text
   GET http://<DNS_DO_INGRESS>/api/notifications
   ```
   *Mostre o array JSON retornando os eventos recém-gravados (Requisitos 6 e 10).*

---

## 6. Estrutura de Arquivos

```text
ms-notifications/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI, endpoints /health, /notifications
│   ├── config.py            # Variáveis (RABBITMQ_HOST, MONGO_URI, PORT)
│   ├── database.py          # Conexão PyMongo e coleção notifications
│   ├── consumer.py          # Worker RabbitMQ em background thread (fila pedidos_events)
│   └── aws/
│       └── eks-cluster-academy.yaml # Configuração eksctl com roles do laboratório
├── aws/
│   └── eks-cluster-academy.yaml     # Cópia do cluster config
├── k8s/
│   ├── 01-mongo.yaml        # Deployment + Service mongo-notification-service + PVC
│   ├── 02-rabbitmq.yaml     # Deployment + Service rabbitmq-service
│   ├── 03-app-deployment.yaml # Deployment com 3 réplicas e limites de recursos
│   ├── 04-app-service.yaml  # Service ms-notifications-service (porta 80 -> 8000)
│   └── 05-ingress.yaml      # Regra NGINX Ingress para /api/notifications(/|$)(.*)
├── Dockerfile               # Imagem python:3.11-slim leve e não-root
├── docker-compose.yml       # Ambiente local mínimo (App + Mongo + RabbitMQ)
├── requirements.txt         # FastAPI, Uvicorn, Pika, PyMongo, Pydantic
└── README.md                # Documentação completa e roteiro de apresentação
```
