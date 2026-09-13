# RFC 003 - Autenticacao Serverless por CPF com JWT

- **Status:** Aceito
- **Escopo:** Identidade e autenticacao de clientes

## Contexto

Clientes precisam acessar a situacao de seus veiculos e aprovar orcamentos sem administrar senhas complexas.

## Decisao

Implementar a autenticacao por CPF em AWS Lambda exposta pelo API Gateway. A funcao valida os digitos do CPF, consulta o cliente ativo no PostgreSQL e emite um JWT assinado.

A API FastAPI valida o token de forma stateless e usa a dependencia `get_current_cliente` nas rotas protegidas.

## Justificativa

- Desacopla autenticacao da API principal.
- Descarta CPFs invalidos antes da consulta ao banco.
- Evita uma consulta de autenticacao a cada chamada protegida.

## Consequencias

- Lambda e API FastAPI precisam compartilhar a mesma `JWT_SECRET_KEY` e algoritmo.
- A chave e os parametros de banco devem ser obtidos pelo SSM Parameter Store.
- O fluxo por CPF exige controles adicionais contra abuso, enumeracao de clientes e exposicao de dados pessoais.

## Referencias

- `PosTechFiap_Mecanica_lambda/src/handler.py`
- `PosTechFiap_Mecanica_lambda/src/token_service.py`
- `PosTechFiap_Mecanica_lambda/template.yaml`
