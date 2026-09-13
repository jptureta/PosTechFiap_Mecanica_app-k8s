# ADR 002 - HPA e Escalabilidade Horizontal em Duas Camadas

- **Status:** Aceito
- **Escopo:** Capacidade da aplicacao e da infraestrutura

## Contexto

A carga varia durante o horario comercial, exigindo capacidade elastica para a API sem manter todos os recursos no pico.

## Decisao

Configurar HPA para a API entre 2 e 10 pods, usando CPU e memoria, e Managed Node Group do EKS entre 2 e 5 nos.

## Consequencias

- A capacidade acompanha a demanda em duas camadas.
- Requests e limits de recursos precisam permanecer definidos para o HPA operar corretamente.
- Readiness, liveness e startup probes sao necessarios para evitar trafego a pods nao prontos.
- O Redis permanece fora dessa estrategia de escalabilidade e continua sendo replica unica.

## Referencias

- `PosTechFiap_Mecanica_app-k8s/k8s/api-hpa.yaml`
- `PosTechFiap_Mecanica_k8s-infra/cluster.tf`
