# Documentação da Arquitetura

## 1. Visão geral

A solução de Oficina Mecânica foi estruturada em quatro repositórios complementares:

- API principal em FastAPI e Kubernetes
- Infraestrutura do banco de dados em Terraform
- Infraestrutura do cluster Kubernetes em Terraform
- Lambda para eventos e processamento assíncrono

A arquitetura foi desenhada para suportar processamento transacional de ordens de serviço, observabilidade em tempo real e escalabilidade horizontal em Kubernetes.

## 2. Objetivos de arquitetura

- Garantir integridade das ordens de serviço e do ciclo de vida de status
- Permitir escalonamento horizontal com HPA em containers Kubernetes
- Separar responsabilidades por domínio e infraestrutura
- Expor saúde da API e métricas para observabilidade
- Registrar eventos e falhas com correlação de requisições
- Utilizar banco relacional para consistência de transações e histórico

## 3. Contexto de negócio e requisitos

A aplicação atende ao fluxo de oficina mecânica:

- cadastro de clientes e veículos
- abertura de ordens de serviço
- inclusão de serviços e peças
- aprovação do orçamento
- alteração de status (Diagnóstico, Execução, Finalização, Entrega)
- histórico de transições
- processamento de notificações e eventos

Requisitos não funcionais relevantes:

- disponibilidade e resiliência em Kubernetes
- latência aceitável da API
- integridade de dados e auditoria
- observabilidade com logs, métricas e alertas
- suporte a componentes cloud-native

## 4. Arquitetura lógica

A arquitetura combina APIs síncronas, fila de processamento, banco relacional e stack de monitoramento.

```mermaid
flowchart LR
    User[Cliente / Operador / Sistema] -->|HTTPS| API[FastAPI API]
    subgraph K8s[Cluster Kubernetes]
        API -->|SQL| DB[(PostgreSQL)]
        API -->|Publish| Redis[(Redis Queue)]
        Worker[Worker de Processamento] -->|Consume| Redis
        Worker -->|Update/Events| DB
        HPA[HorizontalPodAutoscaler]
        API -->|Metrics/Logs| Datadog[Datadog Agent]
    end

    subgraph Cloud[AWS / Infraestrutura Base]
        K8sInfra[Cluster k8s / Node pools]
        DBInfra[DB Infra]
    end

    Lambda[Lambda / Eventos] -->|Metricas| Datadog
    Datadog --> Dash[Dashboards/Alertas]
    HPA --> API
```

### Componentes principais

- API principal: FastAPI em Kubernetes para CRUD, autenticação, regras de negócio e endpoints de ordem de serviço
- Banco de dados: PostgreSQL para dados transacionais e histórico de ordens
- Redis: fila para eventos e processamento assíncrono de notificações
- Worker: consumidor da fila para publicação de eventos e processamento de alertas
- Lambda: processamento serverless de eventos externos e integrações assíncronas
- Datadog: coleta de logs, métricas e alertas, com integração ao Kubernetes

## 5. Diagrama de componentes

```mermaid
flowchart TB
    subgraph Client[Clientes e integrações]
        Browser[Web / Mobile / API Clients]
        Webhook[Webhook / e-mail inbound]
    end

    subgraph Cloud[Ambiente Cloud / Kubernetes]
        Ingress[Ingress / NodePort / Service]
        subgraph App[Namespace oficina]
            API[FastAPI API]
            Worker[Worker de notificações]
            DB[(PostgreSQL)]
            Redis[(Redis)]
        end
        HPA[HPA]
        Agent[Datadog Agent]
    end

    subgraph Monitoring[Observabilidade]
        DD[Datadog]
        Dash[Dashboards]
        Alert[Alertas]
    end

    Browser --> Ingress --> API
    Webhook --> API
    API --> DB
    API --> Redis
    Redis --> Worker
    Worker --> DB

    API --> Agent
    DB --> Agent
    Redis --> Agent
    Worker --> Agent
    Agent --> DD
    DD --> Dash
    DD --> Alert
    HPA --> API
```

### Visão de responsabilidades

- API: regras de negócio, autenticação, transições de status e endpoints externos
- Banco: persistência relacional, integridade, histórico e auditoria
- Redis: fila de eventos e desacoplamento de processamento de notificações
- Datadog: métricas, logs e alertas
- Kubernetes: provisionamento, orquestração, escalabilidade e healthcheck

## 6. Diagrama de sequência: autenticação e abertura de ordem de serviço

```mermaid
sequenceDiagram
    actor Usuario as Usuário / Operador
    participant Auth as Auth API
    participant DB as PostgreSQL
    participant OS as Ordem de Serviço API
    participant Redis as Redis Queue
    participant Worker as Worker
    participant DD as Datadog

    Usuario->>Auth: POST /api/v1/auth/login
    Auth->>DB: Validar credenciais
    DB-->>Auth: usuário + perfil
    Auth-->>Usuario: JWT

    Usuario->>OS: POST /api/v1/ordens-servico
    OS->>DB: validar cliente e veículo
    OS->>DB: inserir OS + itens + status inicial
    OS->>Redis: publicar evento os_criada
    OS-->>Usuario: 201 Created + dados da OS

    Redis-->>Worker: consume evento os_criada
    Worker->>DD: registrar métricas/logs de processamento
    Worker->>DB: registrar histórico / atualizar contexto
```

### Observações do fluxo

- A autenticação utiliza JWT, com foco em sessões curtas e validação no endpoint
- A criação da ordem é transacional no banco para manter consistência
- O evento de ordem criada é assíncrono na fila para notificações e monitoramento sem bloquear o cliente
- O Datadog coleta contexto de cada etapa para metricar tempo e falhas

## 7. RFCs (Request for Comments)

### RFC 001 — Escolha da nuvem e orquestração

- Contexto: a aplicação exige API escalável, tolerante a falhas e deploy em ambiente controlado
- Decisão: usar Kubernetes em ambiente cloud/local com Terraform para provisionamento e `kind` para desenvolvimento local
- Justificativa: separação clara entre infraestrutura e aplicação, maior previsibilidade e suporte a HPA
- Consequências:
  - necessidade de manter manifests e configurações de ambiente versionados
  - mais complexidade operacional comparada a monolito single-instance
  - melhora de resiliência e escalabilidade

### RFC 002 — Escolha do banco de dados

- Contexto: o sistema precisa registrar clientes, veículos, ordens, itens, histórico e status
- Decisão: PostgreSQL como banco principal
- Justificativa: suporte transacional, consultas complexas, integridade referencial, enumeração de status e auditoria
- Consequências:
  - schema relacional bem definido
  - histórico de status persistido
  - melhor aderência para regras de aprovação e estoque

### RFC 003 — Estratégia de autenticação

- Contexto: endpoints sensíveis e gerenciamento de permissões para usuários da oficina
- Decisão: JWT assinado com secret em ambiente controlado
- Justificativa: modelo simples, stateless e compatível com API REST em containers
- Consequências:
  - autenticação eficiente para serviços stateless
  - necessidade de configurar `JWT_SECRET_KEY` por ambiente
  - exigência de expiração e renovação de token

## 8. ADRs (Architecture Decision Records)

### ADR 001 — Padrão de comunicação: HTTP síncrono + fila assíncrona

- Status: Aceito
- Contexto: há operações que precisam resposta imediata e outras que podem ser desacopladas
- Decisão: endpoints síncronos para criação e consulta; fila Redis para eventos de notificações e processamento
- Consequências:
  - API responsiva para usuários finais
  - processamento lateral desacoplado
  - necessidade de lidar com reprocessamento e monitoramento de fila

### ADR 002 — Uso de HPA e escalabilidade horizontal

- Status: Aceito
- Contexto: variação de carga em horários de pico ou múltiplas ordens simultâneas
- Decisão: aplicar `HorizontalPodAutoscaler` com métricas de CPU e memória
- Consequências:
  - maior capacidade em picos de demanda
  - melhor utilização de recursos
  - risco de latência em processos de inicialização caso a app tenha cold start

### ADR 003 — Observabilidade como parte do desenho da aplicação

- Status: Aceito
- Contexto: requisitos de monitoramento, uptime e rastreio de falhas em produção
- Decisão: logs JSON estruturados, métricas de API e Kubernetes, e Datadog como ferramenta central
- Consequências:
  - rastreio de correlação por request ID
  - alertas de falhas em operações críticas
  - operação mais diagnóstica e previsível

## 9. Justificativa formal para a escolha do banco de dados

A decisão por PostgreSQL foi motivada por quatro critérios fundamentais:

1. Integridade transacional
   - o ciclo de vida da ordem de serviço exige transações confiáveis ao alterar status, efetivar estoque e preservar histórico
2. Relacionamento entre entidades
   - o modelo de clientes, veículos, peças, serviços e ordens é naturalmente relacional
3. Auditoria do histórico
   - as transições de status precisam ser preservadas em tabela específica para rastreabilidade
4. Operação em Kubernetes
   - o banco é provisionado como StatefulSet com volume persistente, adequado para ambientes orquestrados

### Modelo relacional ajustado

O desenho relacional foi ajustado para refletir o domínio real de oficina mecânica:

- `clientes` e `veiculos` são entidades independentes relacionadas a múltiplas ordens
- `ordens_servico` centraliza a operação principal
- `ordens_servico_servicos` e `ordens_servico_pecas` modelam itens compostos da ordem
- `ordens_servico_historico` registra todas as mudanças de status
- `servicos` e `pecas` são catalogados e reutilizados por várias ordens

### Diagramas ER

```mermaid
erDiagram
    CLIENTE ||--o{ ORDEM_SERVICO : possui
    VEICULO ||--o{ ORDEM_SERVICO : usa
    ORDEM_SERVICO ||--o{ ORDEM_SERVICO_SERVICO : contem
    SERVICO ||--o{ ORDEM_SERVICO_SERVICO : referencia

    ORDEM_SERVICO ||--o{ ORDEM_SERVICO_PECA : contem
    PECA ||--o{ ORDEM_SERVICO_PECA : referencia

    ORDEM_SERVICO ||--o{ ORDEM_SERVICO_HISTORICO : registra

    CLIENTE {
        int id PK
        string nome
        string cpf_cnpj
        bool ativo
    }

    VEICULO {
        int id PK
        int cliente_id FK
        string placa
        string modelo
    }

    ORDEM_SERVICO {
        int id PK
        int cliente_id FK
        int veiculo_id FK
        string status
        decimal valor_total
        bool orcamento_aprovado
        datetime created_at
        datetime updated_at
        datetime data_finalizacao
        datetime data_entrega
    }

    SERVICO {
        int id PK
        string nome
        decimal valor
        bool ativo
    }

    PECA {
        int id PK
        string nome
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
        string observacao
        datetime data_alteracao
    }
```

### Relacionamentos e impacto

- Um cliente pode ter vários veículos e várias ordens
- Um veículo pode estar associado a várias ordens ao longo do tempo
- Uma ordem possui vários serviços e peças
- Cada alteração de status gera registro no histórico, permitindo auditoria e análise de tempo médio por etapa
- As peças possuem controle de estoque e reserva para impedir inconsistência de aprovação e finalização

## 10. Diagramas de deploy

A solução é implantada em camadas, com infraestrutura separada para cluster, banco e aplicação.

```mermaid
flowchart LR
    subgraph Dev[Desenvolvimento / Operação]
        GH[GitHub Actions]
        TF[Terraform]
        K8S[Manifests Kubernetes]
    end

    subgraph Infra[Infraestrutura]
        Cluster[Cluster kind / Kubernetes]
        Namespace[Namespace oficina]
        Postgres[(PostgreSQL StatefulSet)]
        Redis[(Redis)]
        App[Deployment API]
        Worker[Deployment Worker]
        HPA[HPA]
        DD[Datadog Agent]
    end

    GH --> TF
    GH --> K8S
    TF --> Cluster
    Cluster --> Namespace
    Namespace --> Postgres
    Namespace --> Redis
    Namespace --> App
    Namespace --> Worker
    HPA --> App
    App --> DD
    Worker --> DD
    App --> Postgres
    App --> Redis
```

### Fluxo de implantação

1. O repositório de infraestrutura provisiona o cluster e o namespace.
2. O repositório de banco provisiona o PostgreSQL e seus recursos de rede e storage.
3. O repositório da aplicação publica a imagem e aplica os manifests do Kubernetes.
4. O Datadog Agent coleta métricas e logs dos pods do cluster.
5. O HPA ajusta o número de réplicas conforme demanda de CPU e memória.

## 11. Diagramas da infraestrutura Terraform

### Visão do provisionamento por repositório

```mermaid
flowchart TB
    subgraph K8sInfra[PosTechFiap_Mecanica_k8s-infra]
        K1[cluster.tf]
        K2[providers.tf]
        K3[variables.tf]
        K4[outputs.tf]
        K5[Cluster kind]
    end

    subgraph DBInfra[PosTechFiap_Mecanica_db-infra]
        D1[database.tf]
        D2[variables.tf]
        D3[kubernetes_namespace]
        D4[kubernetes_secret]
        D5[kubernetes_stateful_set Postgres]
        D6[kubernetes_service db]
    end

    subgraph AppRepo[PosTechFiap_Mecanica_app-k8s]
        A1[k8s/configmap.yaml]
        A2[k8s/secrets.yaml]
        A3[k8s/api-deployment.yaml]
        A4[k8s/api-service.yaml]
        A5[k8s/api-hpa.yaml]
        A6[k8s/datadog-agent.yaml]
    end

    K1 --> K5
    K5 --> D3
    D5 --> D6
    D4 --> A2
    A1 --> A3
    A5 --> A3
    A6 --> K5
```

### Infraestrutura de rede e acesso

```mermaid
flowchart LR
    User[Usuário / Cliente] -->|HTTP / HTTPS| NodePort[NodePort 30000]
    NodePort --> Service[api Service]
    Service --> Pod1[API Pod 1]
    Service --> Pod2[API Pod 2]

    Pod1 --> DB[db Service]
    Pod2 --> DB
    Pod1 --> Redis[redis Service]
    Pod2 --> Redis

    Pod1 --> DD[Datadog Agent]
    Pod2 --> DD
    DD --> Datadog[(Datadog)]
    DB --> PG[(PostgreSQL)]
```

### Infraestrutura como código observada

- O cluster é provisionado com Terraform e `kind` em um ambiente local ou cloud
- O namespace da aplicação e os recursos básicos ficam no repositório de infraestrutura Kubernetes
- O banco de dados é provisionado como StatefulSet com armazenamento persistente em um repositório dedicado
- A aplicação recebe os valores via ConfigMap e Secret, reduzindo acoplamento entre código e infraestrutura
- O HPA e a coleta de métricas são componentes centrais no deployment, reforçando a arquitetura de observabilidade

## 12. Conclusão

A arquitetura atual é coerente com os requisitos de negócio e de operação:

- processamento transacional em banco relacional
- desacoplamento de notificações por fila
- escalabilidade via Kubernetes e HPA
- monitoramento centralizado em Datadog
- infraestrutura provisionada por Terraform de forma modular
- documentação técnica que sustenta manutenção e evolução

Essa estrutura reduz risco de inconsistência, melhora observabilidade e permite evolução incremental sem quebrar o domínio do sistema.
