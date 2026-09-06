# Documentação da Arquitetura — Oficina Mecânica (Fase 3)

## 1. Visão Geral

A solução de Oficina Mecânica foi estruturada em quatro repositórios complementares integrados aos serviços gerenciados da AWS:

- **`PosTechFiap_Mecanica_app-k8s`**: Aplicação principal em FastAPI executando em cluster Kubernetes (AWS EKS), com workers assíncronos e HPA.
- **`PosTechFiap_Mecanica_db-infra`**: Infraestrutura Terraform responsável pelo banco de dados gerenciado **AWS RDS PostgreSQL 16**.
- **`PosTechFiap_Mecanica_k8s-infra`**: Infraestrutura Terraform responsável pela VPC dedicada e pelo cluster **AWS EKS com Managed Node Group escalável**.
- **`PosTechFiap_Mecanica_lambda`**: Function Serverless (AWS Lambda) integrada ao **AWS API Gateway** para validação de CPF e autenticação por JWT.

A arquitetura foi desenhada para garantir alta disponibilidade, integridade transacional das ordens de serviço, segurança na borda com autenticação por CPF, e observabilidade em tempo real com Datadog.

---

## 2. Objetivos de Arquitetura

- **Isolamento e Borda Segura:** Autenticação delegada para AWS API Gateway e Lambda Serverless, protegendo as APIs principais via validação de CPF.
- **Escalabilidade em Duas Camadas:** Horizontal Pod Autoscaler (HPA) no Kubernetes para a aplicação (2 a 10 pods) e Auto Scaling no Managed Node Group do EKS (2 a 5 nós EC2).
- **Banco de Dados Gerenciado:** Transações seguras com ACID, storage autoscaling, backups automatizados e isolamento multi-AZ no AWS RDS PostgreSQL.
- **Desacoplamento Orientado a Eventos:** Fila Redis para processamento assíncrono de notificações e histórico de ordens de serviço sem onerar o tempo de resposta da API.
- **Observabilidade Unificada:** Coleta de métricas de negócio, latência, recursos de Kubernetes e logs estruturados em JSON correlacionados por `X-Request-ID` via Datadog.

---

## 3. Contexto de Negócio e Requisitos

A aplicação gerencia o ciclo completo de ordens de serviço (OS) de uma oficina mecânica:
- Cadastro e acompanhamento de clientes e veículos.
- Abertura de ordens de serviço com orçamento de peças e serviços.
- Aprovação/recusa de orçamentos (inclusive via webhooks externos).
- Ciclo de vida e máquina de estados das ordens (`Recebida` → `Em Diagnóstico` → `Aguardando Aprovação` → `Em Execução` → `Finalizada` → `Entregue` / `Cancelada`).
- Gestão de estoque com reserva automática de peças na aprovação e baixa na finalização.
- Relatórios de tempo médio por etapa e volumes operacionais.

---

## 4. Arquitetura Lógica

```mermaid
flowchart TD
    Cliente[Cliente / Sistema Externo] -->|1. POST /auth/cpf| APIGW[AWS API Gateway HTTP]
    APIGW -->|Trigger| Lambda[AWS Lambda Auth]
    Lambda -->|Valida CPF & Consulta Cliente| RDS[(AWS RDS PostgreSQL 16)]
    Lambda -->>|Retorna JWT com sub: CPF| Cliente

    Cliente -->|2. Chamadas com Bearer JWT| APIGW
    APIGW -->|Proxy| EKS_API[FastAPI API no AWS EKS]

    subgraph EKS[Cluster AWS EKS]
        EKS_API -->|Transacoes SQL| RDS
        EKS_API -->|Publica Eventos| Redis[(Redis Queue)]
        Worker[Worker de Notificacoes] -->|Consome Eventos| Redis
        Worker -->|Atualiza Historico| RDS
        HPA[Horizontal Pod Autoscaler] -.->|Auto Scale 2-10| EKS_API
        DDAgent[Datadog Agent DaemonSet]
    end

    EKS_API -->|Métricas & Logs JSON| DDAgent
    Lambda -->|Métricas StatsD| DatadogCloud[(Datadog SaaS)]
    DDAgent --> DatadogCloud
    DatadogCloud --> Dashboards[Dashboards & Alertas P1/P2]
```

---

## 5. Diagrama de Componentes

Visão integrada de nuvem AWS, APIs, banco de dados e monitoramento:

```mermaid
flowchart TB
    subgraph Borda[Borda & Autenticação AWS]
        APIGW[AWS API Gateway\nHTTP API - prod]
        LambdaAuth[AWS Lambda\nauth_cpf_handler / Python 3.12]
        SSM[AWS SSM Parameter Store\n/oficina/jwt/* & /oficina/db/*]
    end

    subgraph VPC_EKS[AWS VPC - Cluster EKS]
        subgraph Subnets_Publicas[Subnets Multi-AZ]
            NLB[AWS Network Load Balancer / Ingress]
            subgraph NodeGroup[EKS Managed Node Group\nt3.medium / Auto Scaling 2 a 5 nós]
                subgraph Pods[Namespace oficina]
                    API[FastAPI API Pods\nMin 2 - Max 10 HPA]
                    Worker[Worker Pods\nNotificações]
                    Redis[(Redis Pod / Service)]
                end
                DDAgent[Datadog Agent\nDaemonSet]
            end
        end
    end

    subgraph VPC_Data[AWS VPC - Camada de Dados]
        subgraph SubnetGroup[DB Subnet Group Multi-AZ]
            RDS[(AWS RDS PostgreSQL 16\ngp3 Storage Autoscaling)]
        end
        RDS_SG[Security Group RDS\nPorta 5432 restrita]
    end

    subgraph Observabilidade[Datadog Monitoring SaaS]
        DD_Metrics[Métricas de Latência & Uptime]
        DD_K8s[Métricas de CPU & Memória EKS]
        DD_Logs[Logs Estruturados JSON\nX-Request-ID]
        DD_Monitors[Alertas Declarativos P1/P2]
    end

    %% Relações
    APIGW -->|/auth/cpf| LambdaAuth
    SSM -.->|Injeta Segredos| LambdaAuth
    LambdaAuth -->|Consulta Cliente| RDS
    APIGW -->|/api/v1/*| NLB
    NLB --> API

    API -->|Pool de Conexões| RDS
    API -->|Eventos| Redis
    Redis --> Worker
    Worker --> RDS

    API --> DDAgent
    Worker --> DDAgent
    DDAgent --> DD_Metrics
    DDAgent --> DD_K8s
    DDAgent --> DD_Logs
    LambdaAuth --> DD_Metrics
    DD_Metrics --> DD_Monitors
```

---

## 6. Diagrama de Sequência: Autenticação por CPF e Abertura de OS

Fluxo de ponta a ponta demonstrando a interação entre cliente, API Gateway, Lambda, banco de dados e cluster EKS:

```mermaid
sequenceDiagram
    autonumber
    actor Cliente as Cliente
    participant APIGW as AWS API Gateway
    participant Lambda as AWS Lambda (Auth)
    participant RDS as AWS RDS PostgreSQL
    participant EKS as FastAPI API (EKS)
    participant Redis as Redis Queue
    participant Worker as Worker (Notificações)
    participant DD as Datadog

    %% Autenticação
    Note over Cliente,RDS: 1. Fluxo de Autenticação Serverless via CPF
    Cliente->>APIGW: POST /auth/cpf {"cpf": "529.982.247-25"}
    APIGW->>Lambda: Dispara evento HTTP POST
    Lambda->>Lambda: validar_cpf(cpf) [Dígitos Verificadores]
    alt CPF Inválido
        Lambda-->>APIGW: 422 Unprocessable Entity
        APIGW-->>Cliente: 422 CPF inválido
    end

    Lambda->>RDS: SELECT id, nome, ativo FROM clientes WHERE cpf_cnpj = '52998224725'
    alt Cliente Inexistente ou Inativo
        RDS-->>Lambda: null ou ativo=false
        Lambda-->>APIGW: 404 Not Found / 403 Forbidden
        APIGW-->>Cliente: Erro de autenticação
    end
    RDS-->>Lambda: {id: 42, nome: "Maria Silva", ativo: true}
    Lambda->>Lambda: jwt.encode({"sub": "52998224725", "tipo": "cliente", "id": 42})
    Lambda-->>APIGW: 200 OK {"access_token": "eyJ...", "token_type": "bearer"}
    APIGW-->>Cliente: Retorna Access Token JWT

    %% Abertura de OS
    Note over Cliente,DD: 2. Abertura de Ordem de Serviço com Token JWT
    Cliente->>APIGW: POST /api/v1/ordens-servico [Header: Authorization Bearer eyJ...]
    APIGW->>EKS: Roteia requisição para a API
    EKS->>EKS: decode_access_token(token) & valida assinatura JWT
    EKS->>RDS: Inicia transação: valida veículo, insere OS e itens de serviço/peça
    RDS-->>EKS: OS criada com status 'recebida'
    EKS->>Redis: Publica evento {tipo: "os_criada", dados: {ordem_servico_id: 101}}
    EKS->>DD: Emite métricas: oficina.api.requests_total e latência HTTP
    EKS-->>Cliente: 201 Created {"id": 101, "status": "recebida", "valor_total": ...}

    %% Processamento Assíncrono
    Note over Redis,Worker: 3. Processamento em Segundo Plano
    Redis-->>Worker: Consome evento 'os_criada'
    Worker->>DD: Registra log JSON com request_id e métrica de transição de status
    Worker->>RDS: Registra evento no histórico de auditoria
```

---

## 7. RFCs (Request for Comments)

### RFC 001 — Adoção da AWS e Orquestração com AWS EKS
- **Contexto:** A solução necessita de disponibilidade em nuvem, facilidade de deploy contínuo (CI/CD) e suporte nativo a escalabilidade elástica tanto de instâncias de aplicação quanto de nós computacionais.
- **Decisão:** Utilizar a **AWS** como provedor de nuvem e o **AWS EKS (Elastic Kubernetes Service)** provisionado via Terraform com subnets multi-AZ e Managed Node Group.
- **Justificativa:** 
  - O EKS oferece um control plane gerenciado com SLA de 99,95%, eliminando o overhead de manutenção de nós master.
  - O Managed Node Group permite atualização segura de nós, drenagem automatizada e auto scaling nativo integrado com o Cluster Autoscaler.
- **Consequências:**
  - Configuração de VPC com subnets públicas e privadas em no mínimo 2 Availability Zones.
  - Uso de IAM Roles para Service Accounts (IRSA) e permissões granulares por política de menor privilégio.

### RFC 002 — Banco de Dados Gerenciado: AWS RDS PostgreSQL 16
- **Contexto:** A aplicação de oficina mecânica gerencia dados transacionais sensíveis (pedidos, valores, estoque, histórico de ordens) que exigem conformidade estrita com as propriedades ACID.
- **Decisão:** Adotar o **AWS RDS PostgreSQL 16** como banco de dados relacional gerenciado, provisionado via Terraform no repositório `PosTechFiap_Mecanica_db-infra`.
- **Justificativa:**
  - Evita o risco de perda de dados associado a bancos self-hosted em Kubernetes (StatefulSets).
  - Fornece backups automáticos diários com retenção configurável, patches de segurança e recuperação pontual no tempo (PITR).
  - Storage autoscaling com discos `gp3`, iniciando em 20 GiB e expandindo dinamicamente até 100 GiB sem parada.
- **Consequências:**
  - Isolamento de rede em DB Subnet Group privado e Security Groups restritos à porta 5432.
  - Gerenciamento seguro de credenciais master através de variáveis protegidas no Terraform e AWS SSM Parameter Store.

### RFC 003 — Estratégia de Autenticação Serverless sem Senha por CPF
- **Contexto:** Os clientes da oficina necessitam consultar o andamento e aprovar orçamentos de seus veículos de forma simples, sem necessidade de memorização de senhas complexas, porém mantendo a proteção contra acessos indevidos.
- **Decisão:** Implementar a autenticação de clientes via **CPF** através de uma **AWS Lambda** exposta via **AWS API Gateway**, emitindo tokens JWT assinados compartilhados com o EKS.
- **Justificativa:**
  - Desacopla o fluxo de autenticação da aplicação principal (reduzindo carga na API principal em caso de ataques de força bruta).
  - A Lambda valida matematicamente o CPF antes de qualquer consulta ao banco, descartando requisições inválidas com custo mínimo de computação.
  - O token JWT gerado carrega a claim `tipo: "cliente"` e `sub: "<cpf>"`, sendo validado de forma stateless pela API FastAPI sem requisições adicionais de autenticação por chamada.
- **Consequências:**
  - Compartilhamento seguro da `JWT_SECRET_KEY` entre Lambda e EKS via AWS SSM Parameter Store.
  - Criação de dependência FastAPI dedicada (`get_current_cliente`) para proteger rotas específicas de clientes.

---

## 8. ADRs (Architecture Decision Records)

### ADR 001 — Padrão de Comunicação Híbrido: HTTP Síncrono + Fila Redis
- **Status:** Aceito
- **Contexto:** Operações de CRUD e consultas de status demandam retorno imediato ao usuário, enquanto notificações por e-mail e emissão de alertas não devem atrasar a resposta da API.
- **Decisão:** Comunicação HTTP RESTful síncrona para operações de cliente e publicação assíncrona de eventos de domínio em fila **Redis** consumida por workers dedicados.
- **Consequências:**
  - Tempo de resposta da API abaixo de 100ms para abertura de ordens.
  - Resiliência: se o serviço de notificações falhar, a mensagem permanece na fila Redis para reprocessamento sem perda de dados.

### ADR 002 — Uso de HPA e Escalabilidade Horizontal em Duas Camadas
- **Status:** Aceito
- **Contexto:** A carga na oficina mecânica varia fortemente ao longo do dia, com picos de abertura e fechamento de ordens nos horários comerciais.
- **Decisão:** Configurar o **Horizontal Pod Autoscaler (HPA)** nos pods da API (2 a 10 réplicas baseadas em CPU > 50% e Memória > 80%) e **Auto Scaling Group** no EKS Node Group (2 a 5 nós EC2).
- **Consequências:**
  - Garantia de capacidade de processamento elástica sem desperdício de recursos ociosos.
  - Necessidade de probes adequadas (`readinessProbe` e `livenessProbe`) para evitar envio de tráfego a pods em inicialização.

### ADR 003 — Observabilidade Nativa com Datadog e Correlação por Request ID
- **Status:** Aceito
- **Contexto:** Rastreabilidade fim a fim de transações e capacidade de resposta rápida a incidentes operacionais.
- **Decisão:** Instrumentação de logs estruturados em formato JSON com propagação do header `X-Request-ID`, métricas DogStatsD customizadas e Datadog Agent DaemonSet no cluster EKS.
- **Consequências:**
  - Permite correlacionar chamadas na API, erros no banco e mensagens consumidas no worker através do mesmo identificador (`req-...`).
  - Painéis executivos com volume de ordens, tempos médios e alertas automáticos P1/P2.

---

## 9. Justificativa Formal para a Escolha do Banco de Dados

A escolha do **PostgreSQL 16 (AWS RDS)** como tecnologia de persistência é sustentada por:

1. **Garantias ACID e Consistência Transacional:** O ciclo de vida de uma ordem de serviço envolve múltiplas tabelas (OS, itens de peça, itens de serviço, histórico e estoque). O PostgreSQL garante que reservas de peças e baixas de estoque ocorram atomicamente com a mudança de status.
2. **Integridade Referencial Rigorosa:** Foreign keys garantem que peças e serviços não sejam excluídos enquanto houver ordens vinculadas, e que veículos e ordens pertençam a clientes válidos.
3. **Auditoria Contínua:** Tabela de histórico dedicada (`ordens_servico_historico`) que armazena cada mudança de estado com timestamp e observações, viabilizando o cálculo preciso de métricas operacionais.

### Diagrama Entidade-Relacionamento (ER)

```mermaid
erDiagram
    CLIENTE ||--o{ VEICULO : possui
    CLIENTE ||--o{ ORDEM_SERVICO : solicita
    VEICULO ||--o{ ORDEM_SERVICO : atende
    ORDEM_SERVICO ||--o{ ORDEM_SERVICO_SERVICO : contem
    SERVICO ||--o{ ORDEM_SERVICO_SERVICO : referencia
    ORDEM_SERVICO ||--o{ ORDEM_SERVICO_PECA : contem
    PECA ||--o{ ORDEM_SERVICO_PECA : referencia
    ORDEM_SERVICO ||--o{ ORDEM_SERVICO_HISTORICO : audita

    CLIENTE {
        int id PK
        string nome
        string cpf_cnpj UK
        string email
        string telefone
        string endereco
        bool ativo
        datetime created_at
        datetime updated_at
    }

    VEICULO {
        int id PK
        int cliente_id FK
        string placa UK
        string marca
        string modelo
        int ano
        string cor
    }

    ORDEM_SERVICO {
        int id PK
        int cliente_id FK
        int veiculo_id FK
        string status
        decimal valor_total
        bool orcamento_aprovado
        text observacoes
        datetime created_at
        datetime updated_at
        datetime data_finalizacao
        datetime data_entrega
    }

    SERVICO {
        int id PK
        string nome
        text descricao
        decimal valor
        int tempo_estimado_minutos
        bool ativo
    }

    PECA {
        int id PK
        string nome
        string codigo_referencia
        int quantidade_estoque
        int quantidade_reservada
        int estoque_minimo
        decimal valor_unitario
        bool ativo
    }

    ORDEM_SERVICO_SERVICO {
        int id PK
        int ordem_servico_id FK
        int servico_id FK
        int quantidade
        decimal valor_unitario
        decimal valor_total
    }

    ORDEM_SERVICO_PECA {
        int id PK
        int ordem_servico_id FK
        int peca_id FK
        int quantidade
        decimal valor_unitario
        decimal valor_total
    }

    ORDEM_SERVICO_HISTORICO {
        int id PK
        int ordem_servico_id FK
        string status_anterior
        string status_novo
        text observacao
        datetime data_alteracao
    }
```

---

## 10. Estrutura Modular dos Repositórios e CI/CD

A infraestrutura e o ciclo de vida de deploy são segregados de acordo com os 4 repositórios:

```mermaid
flowchart LR
    subgraph Repo1[PosTechFiap_Mecanica_lambda]
        L_Code[Código SAM / Python]
        L_CI[GitHub Actions CI/CD]
        L_Target[AWS Lambda + API Gateway]
    end

    subgraph Repo2[PosTechFiap_Mecanica_db-infra]
        DB_Code[Terraform RDS]
        DB_CI[GitHub Actions CI/CD]
        DB_Target[AWS RDS PostgreSQL 16]
    end

    subgraph Repo3[PosTechFiap_Mecanica_k8s-infra]
        K8S_Code[Terraform EKS & VPC]
        K8S_CI[GitHub Actions CI/CD]
        K8S_Target[AWS EKS Cluster & Node Group]
    end

    subgraph Repo4[PosTechFiap_Mecanica_app-k8s]
        App_Code[FastAPI & Manifests K8s]
        App_CI[GitHub Actions CI/CD]
        App_Target[Deploy Pods no AWS EKS]
    end

    L_Code --> L_CI --> L_Target
    DB_Code --> DB_CI --> DB_Target
    K8S_Code --> K8S_CI --> K8S_Target
    App_Code --> App_CI --> App_Target
```

Cada repositório possui esteira com execução de testes, validação de IaC (`validate`/`plan`) e deploy automático nos ambientes de **homologação** e **produção**.
