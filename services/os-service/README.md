# Ordem de Serviço

Serviço independente de ordens de serviço e coordenador da Saga. O banco deste
serviço é a única fonte de verdade para ordens, estados da Saga e histórico.

## Executar localmente

```powershell
docker compose up --build
```

A API fica em `http://localhost:8001/docs`. O compose cria um PostgreSQL exclusivo
para OS. Para desenvolvimento sem Docker, defina `DATABASE_URL` e execute
`alembic upgrade head` e `uvicorn app.main:app --reload --port 8001`.

## Fluxo distribuído

1. `POST /orders` persiste a OS e solicita orçamento ao Billing. Falha remota
   mantém a OS em `QUOTE_PENDING`; `POST /orders/{id}/retry-quote` permite retomar.
2. O Billing comunica aprovação e pagamento verificado a endpoints internos
   autenticados por `INTERNAL_SERVICE_TOKEN`.
3. Após pagamento, OS reserva peças no Inventory. Em falha, solicita compensação
   ao Billing e persiste `COMPENSATION_PENDING` ou `CANCELLED`; não declara
   reembolso efetivado sem confirmação de um provedor de pagamento.

As chamadas HTTP são idempotentes por `order_id` e `payment_id`. Configure
`BILLING_URL`, `INVENTORY_URL` e o mesmo `INTERNAL_SERVICE_TOKEN` nos três serviços.
Configure também `JWT_SECRET_KEY` e `JWT_ALGORITHM` iguais aos usados pela
Lambda/API legada. Clientes só podem abrir/consultar as próprias OS; alterações
operacionais de status exigem token de administrador.

Antes de abrir uma OS, cadastre preços/catálogo e estoque no Inventory usando o
token interno. O corpo da OS aceita apenas `customer_id`, `vehicle_id` e itens
`{kind: PART|SERVICE, sku, quantity}`; nome/preço são obtidos do Inventory e
congelados no orçamento.

## Testes e entrega

`uv sync --dev && uv run pytest`. O workflow GitHub Actions executa testes,
publica a imagem no GHCR nas branches `homologacao` e `production` e atualiza o
Deployment Kubernetes correspondente. Configure os secrets de registry/AWS/
Kubernetes e `DATABASE_URL`, URLs internas e token no ambiente de deploy.
O segredo JWT e o algoritmo também devem corresponder ao emissor legado.
O namespace também precisa ter o secret `ghcr-pull` com permissão de leitura
para imagens privadas no GHCR.

O RDS exclusivo é definido em `infra/`. Valide com
`terraform -chdir=infra init -backend=false`, `terraform -chdir=infra validate`
e `terraform -chdir=infra plan` após fornecer as variáveis requeridas. O apply
exige backend de estado remoto e revisão do plano antes de provisionar recursos.
