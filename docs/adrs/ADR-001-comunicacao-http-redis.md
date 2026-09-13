# ADR 001 - Comunicacao HTTP Sincrona e Fila Redis

- **Status:** Aceito com ressalva de durabilidade
- **Escopo:** Comunicacao entre API e processamento em segundo plano

## Contexto

Operacoes de CRUD e consultas precisam de resposta imediata, enquanto notificacoes e tarefas de segundo plano nao devem aumentar a latencia da API.

## Decisao

Usar HTTP REST sincrono para as operacoes da API e publicar eventos de dominio em uma fila Redis consumida por workers.

## Consequencias

- A API pode responder apos persistir a OS e publicar o evento.
- O worker processa notificacoes e atualizacoes de historico fora do ciclo da requisicao.
- O Redis atual e um Deployment de replica unica, sem volume persistente configurado.
- A fila nao garante durabilidade ou reprocessamento sem perda apos falha do pod. Persistencia, alta disponibilidade e retry explicito sao pendencias.

## Referencias

- `PosTechFiap_Mecanica_app-k8s/app/worker.py`
- `PosTechFiap_Mecanica_app-k8s/k8s/redis-deployment.yaml`
