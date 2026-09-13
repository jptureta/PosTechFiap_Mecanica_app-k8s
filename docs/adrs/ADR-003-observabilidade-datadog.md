# ADR 003 - Observabilidade com Datadog e Request ID

- **Status:** Aceito
- **Escopo:** Logs, metricas e monitoramento operacional

## Contexto

A equipe precisa rastrear transacoes, diagnosticar falhas e acompanhar indicadores da API, dos workers e do cluster Kubernetes.

## Decisao

Usar logs estruturados em JSON, propagacao de `X-Request-ID`, metricas DogStatsD e Datadog Agent como DaemonSet no EKS. Dashboards e monitores sao mantidos como configuracao declarativa.

## Consequencias

- Chamadas da API, processamento do worker e alertas podem ser correlacionados pelo mesmo identificador.
- O Datadog recebe metricas de latencia, disponibilidade, negocio e recursos do cluster.
- A operacao depende de configuracao correta do Agent, credenciais e conectividade com o Datadog.
- Os monitores devem ser revisados conforme os limites reais de negocio e infraestrutura.

## Referencias

- `PosTechFiap_Mecanica_app-k8s/app/observability.py`
- `PosTechFiap_Mecanica_app-k8s/k8s/datadog-agent.yaml`
- `PosTechFiap_Mecanica_app-k8s/datadog-monitors.yaml`
