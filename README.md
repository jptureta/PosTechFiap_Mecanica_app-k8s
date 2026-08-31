# Repositório da Aplicação Principal

Este repositório concentra a aplicação principal do sistema Oficina Mecânica, executando em FastAPI e disponibilizada em Kubernetes.

## Objetivo

- manter a API e a lógica do domínio isoladas do restante da infraestrutura
- empacotar a aplicação em container
- publicar a imagem em um registry privado ou GHCR
- aplicar os manifests do Kubernetes em homologação e produção
- padronizar o deploy por branch e ambiente

## Stack principal

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Docker
- Kubernetes
- GitHub Actions

## Estrutura do repositório

```text
repo-app-k8s/
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── alembic/
├── app/
├── k8s/
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── README.md
└── .gitignore
```

## Fluxo de entrega

```text
feature/* -> PR -> homologacao -> deploy automático
feature/* -> PR -> main -> deploy automático em produção
```

## Branches

- `homologacao`
- `main`

## CI/CD

O workflow deste repositório executa:

1. instalação das dependências
2. testes automatizados da API
3. build da imagem Docker
4. push da imagem para o registry
5. deploy dos manifests em Kubernetes

## Secrets obrigatórios

- `KUBE_CONFIG`
- `DB_PASSWORD`
- `JWT_SECRET_KEY`

## Variáveis de ambiente

O projeto usa `.env.example` como referência para configuração local. Em produção e homologação, os valores devem ser enviados via GitHub Actions secrets e environment variables.

## Como executar localmente

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate no Windows
pip install -r requirements.txt  # se houver
uv sync --dev
uv run pytest
```

## Observações

- a branch `main` é protegida e exige PR
- deploy em produção só acontece após aprovação e checks verdes
- o workflow deve validar a API antes do rollout no cluster
- os manifests do Kubernetes estão na pasta `k8s/` e devem ser aplicados somente após a infraestrutura base estar disponível

## Regras de proteção

- commits diretos bloqueados
- merge somente via Pull Request
- revisão mínima obrigatória
- status checks obrigatórios
- bloqueio de force push
- bloqueio de exclusão da branch
