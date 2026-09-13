# RFC 004 - Endurecimento da Conectividade do RDS

- **Status:** Proposto
- **Escopo:** Seguranca de rede e acesso ao banco

## Problema

A configuracao atual do Terraform expõe a instancia RDS publicamente e permite conexoes de qualquer origem na porta 5432, embora a arquitetura pretenda isolar o banco.

## Proposta

- Definir `publicly_accessible = false`.
- Usar subnets privadas no DB Subnet Group.
- Restringir o Security Group as origens reais da aplicacao no EKS e da Lambda/VPC.
- Manter acesso administrativo por canal controlado, sem abrir a porta para a internet.
- Validar as permissoes IAM de leitura dos parametros no SSM.

## Criterios de aceite

- Nenhuma regra de entrada `0.0.0.0/0` na porta 5432.
- Conectividade validada a partir dos componentes autorizados.
- Deploy e healthchecks funcionando em homologacao.
- Documentacao e Terraform descrevendo o mesmo estado.

## Riscos e dependencias

A mudanca depende de subnets privadas e de regras de Security Group que permitam o acesso efetivo da Lambda e dos pods da API.
