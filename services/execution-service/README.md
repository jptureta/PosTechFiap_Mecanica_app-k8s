# Execução e Produção (Execution Service)

Microsserviço responsável pelo gerenciamento da fila de atendimento e pela esteira operacional da oficina mecânica durante as etapas de diagnóstico, reparo e conclusão dos serviços veiculares.

---

## Responsabilidades Principais

1. **Gerenciamento da Fila de Execução da OS**:
   - `POST /executions`: Registra a OS aprovada na fila de atendimento com nível de prioridade configurável.
   - `POST /executions/next`: Desenfileira o próximo serviço a ser executado segundo a ordem de prioridade e chegada (FIFO).
   - `GET /executions`: Consulta e monitoramento do pátio operacional e da fila de espera.

2. **Atualização de Status durante Diagnóstico e Reparos**:
   - `PATCH /executions/{execution_id}/status`: Registra as transições de status da execução (`QUEUED` -> `DIAGNOSING` -> `REPAIRING`) com notas técnicas do mecânico e histórico auditável.
   - Sincroniza em tempo real com o `os-service` via endpoint interno autenticado (`/internal/orders/{order_id}/status`).

3. **Comunicação de Finalização ao OS Service**:
   - `POST /executions/{execution_id}/complete`: Finaliza o ciclo de execução operacional na oficina e dispara uma notificação HTTP síncrona/idempotente ao `os-service`, transitando a OS para o status final `COMPLETED`.

---

## Arquitetura de Banco de Dados e Persistência Poliglota

Para atender aos requisitos arquiteturais de banco próprio por microsserviço e uso obrigatório de bancos relacionais e não-relacionais:

| Tipo | Tecnologia | Aplicação no Ecossistema | Justificativa Técnica |
| :--- | :--- | :--- | :--- |
| **SQL (Relacional)** | **PostgreSQL (AWS RDS)** | `os-service`, `billing-service`, `inventory-service` | Transações estritas ACID, constraints financeiras de alta precisão (`Numeric`), locks pessimistas contra concorrência de estoque e integridade referencial com histórico auditável. |
| **NoSQL (Em Memória / Key-Value)** | **Redis 7** | `execution-service` (Fila Operacional) | Utilizado em `execution-service` para gerenciar a fila atômica FIFO de alta performance de atendimento da oficina (`RPUSH` e `LPOP` na chave `execution:queue`). |
| **NoSQL (Document Store)** | **MongoDB / AWS DynamoDB** | `execution-service` (Laudos e Diagnósticos) | **Sugestão arquitetural recomendada**: Diagnósticos automotivos e inspeções possuem esquema altamente flexível e dinâmico (códigos de erro OBD-II, leituras de scanners, checklists veiculares com campos variáveis por montadora). Um banco de documentos NoSQL elimina migrações rígidas de DDL e permite escalabilidade horizontal para relatórios de serviço não estruturados. |

---

## Execução Local

```powershell
# Execução via Docker Compose integrado:
docker compose -f docker-compose.yml -f docker-compose.microservices.yml up --build execution-service execution-db execution-queue
```

A API do serviço fica disponível em `http://localhost:8004/docs`.

### Testes Automatizados
```powershell
uv run pytest
```

