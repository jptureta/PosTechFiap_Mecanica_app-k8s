# RFC 001 - Adocao da AWS e AWS EKS

- **Status:** Aceito
- **Escopo:** Plataforma de nuvem e orquestracao

## Contexto

A solucao precisa de disponibilidade em nuvem, deploy continuo e escalabilidade elastica da aplicacao e dos nos computacionais.

## Decisao

Utilizar a AWS como provedor de nuvem e o AWS EKS provisionado via Terraform, com VPC multi-AZ e Managed Node Group.

O acesso externo a aplicacao ocorre pelo AWS API Gateway, que utiliza VPC Link, NLB interno e NodePort 30000 para chegar aos pods FastAPI.

## Justificativa

- Control plane gerenciado, reduzindo a operacao de componentes mestres.
- Managed Node Group com atualizacao e drenagem controladas.
- Integracao com HPA e escalabilidade dos nos.

## Consequencias

- A topologia depende de VPC, VPC Link, NLB e configuracoes de Security Group coerentes.
- O uso de IRSA e permissoes IAM de menor privilegio permanece como diretriz de seguranca.
- Custos e complexidade operacional sao maiores que em uma aplicacao executada diretamente em uma instancia.

## Referencias

- `PosTechFiap_Mecanica_k8s-infra/cluster.tf`
- `PosTechFiap_Mecanica_k8s-infra/nlb.tf`
- `PosTechFiap_Mecanica_lambda/template.yaml`
