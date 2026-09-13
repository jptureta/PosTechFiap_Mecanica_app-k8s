# RFC 002 - Banco de Dados Gerenciado AWS RDS PostgreSQL 16

- **Status:** Aceito com ressalva de seguranca
- **Escopo:** Persistencia transacional

## Contexto

A aplicacao gerencia ordens de servico, estoque, valores e historico de auditoria. Esses dados exigem consistencia transacional e integridade referencial.

## Decisao

Adotar AWS RDS PostgreSQL 16, provisionado por Terraform no repositorio `PosTechFiap_Mecanica_db-infra`.

## Justificativa

- Suporte a transacoes ACID e foreign keys.
- Backups automaticos e recuperacao pontual configuravel.
- Storage autoscaling com gp3.
- Menor risco operacional que manter um banco self-hosted em Kubernetes.

## Estado atual e ressalva

O DB Subnet Group e multi-AZ, mas a implementacao atual define `publicly_accessible = true` e libera a porta 5432 para `0.0.0.0/0`. Essa configuracao e um risco e nao representa o estado-alvo de producao.

## Consequencias

- A aplicacao e a Lambda dependem da conectividade com o endpoint RDS.
- Credenciais sao consumidas pelo AWS SSM Parameter Store.
- O acesso de rede precisa ser endurecido conforme a RFC 004.

## Referencias

- `PosTechFiap_Mecanica_db-infra/database.tf`
- `PosTechFiap_Mecanica_app-k8s/alembic/versions/001_initial_schema.py`
