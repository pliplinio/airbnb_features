# Airbnb Features

Feature Store para dados do Airbnb construída sobre **Databricks Unity Catalog**, usando **Databricks Connect (serverless)** para desenvolvimento local e **UV** para gerenciamento de dependências.

---

## Arquitetura

```
airbnb_features/
├── .databricks/
│   └── profile.json              # Configuração do Databricks Connect
├── src/
│   └── airbnb_features/
│       ├── common/
│       │   └── spark_session.py   # SparkSession via Databricks Connect (serverless)
│       ├── landing/
│       │   └── ingest_listings.py # Leitura de airbnb.landing.listings
│       ├── features/
│       │   └── host_features.py   # Construção de features por host
│       └── utils/
│           └── feature_store.py   # Publicação no Feature Store
├── notebooks/
│   └── explore_listings.ipynb     # Análise exploratória dos dados
├── tests/
│   ├── test_host_features.py
│   └── test_listing_features.py
├── pyproject.toml                 # Dependências e config (UV + Hatch)
├── uv.lock                        # Lock file do UV
├── .python-version                # Python 3.12
├── .env                           # Credenciais (NÃO versionado)
└── .gitignore
```

---

## Unity Catalog — Namespaces

| Camada      | Tabela                           | Descrição                                  |
|-------------|----------------------------------|--------------------------------------------|
| **Landing** | `airbnb.landing.listings`        | Dados brutos de listings do Airbnb         |
| **Features**| `airbnb.features.listing_features` | Feature table publicada no Feature Store |

---

## Pré-requisitos

- **Python 3.12+**
- **UV** (package manager)
- Acesso ao workspace Databricks com Unity Catalog habilitado
- Personal Access Token (PAT) do Databricks

---

## Setup

### 1. Instalar o UV

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Instalar dependências

```bash
# Instala todas as dependências (produção + dev)
uv sync --extra dev
```

Isso cria automaticamente um `.venv/` e instala todos os pacotes definidos no `pyproject.toml`.

### 3. Configurar credenciais

Crie o arquivo `.env` na raiz do projeto (já está no `.gitignore`):

```env
DATABRICKS_HOST=https://dbc-704623d7-21a0.cloud.databricks.com/
DATABRICKS_TOKEN=dapi_seu_token_aqui
```

> **Não é necessário** `DATABRICKS_CLUSTER_ID` — o projeto usa **serverless compute**.

---

## Databricks Connect (Serverless)

O projeto utiliza o [Databricks Connect](https://docs.databricks.com/en/dev-tools/databricks-connect/index.html) para executar código PySpark localmente, com o processamento rodando no **serverless compute** do Databricks. Isso elimina a necessidade de manter um cluster dedicado.

### Como funciona

```python
from airbnb_features.common.spark_session import get_spark

spark = get_spark()
df = spark.read.table("airbnb.landing.listings")
df.show()
```

A função `get_spark()` cria uma `DatabricksSession` configurada para serverless:

```python
DatabricksSession.builder
    .host("https://dbc-704623d7-21a0.cloud.databricks.com/")
    .token(os.getenv("DATABRICKS_TOKEN"))
    .serverless(True)
    .getOrCreate()
```

### Testar a conexão

```bash
uv run python -c "from airbnb_features.common.spark_session import get_spark; spark = get_spark(); spark.sql('SELECT 1').show()"
```

### Versão do databricks-connect

O serverless requer `databricks-connect>=18.0,<18.1`. Versões mais recentes (18.1+) não suportam serverless.

---

## Feature Store

O projeto utiliza o [Databricks Feature Engineering](https://docs.databricks.com/en/machine-learning/feature-store/index.html) para publicar feature tables no Unity Catalog.

### Fluxo

```
airbnb.landing.listings
        │
        ▼
  build_host_features()      ← src/airbnb_features/features/host_features.py
        │
        ▼
  publish_feature_table()    ← src/airbnb_features/utils/feature_store.py
        │
        ▼
airbnb.features.listing_features   (Unity Catalog Feature Table)
```

### Construção de features

`host_features.py` agrega os dados de listings por `host_id`:

| Feature                    | Descrição                              |
|----------------------------|----------------------------------------|
| `total_listings`           | Total de imóveis do host               |
| `total_reviews`            | Soma de reviews de todos os imóveis    |
| `total_reviews_last_12m`   | Reviews nos últimos 12 meses           |

### Publicação

`feature_store.py` expõe a função `publish_feature_table()` que recebe um DataFrame e publica como feature table no Unity Catalog com metadados (description, tags).

```python
from airbnb_features.landing.ingest_listings import read_listings
from airbnb_features.features.host_features import build_host_features
from airbnb_features.utils.feature_store import publish_feature_table

df = read_listings()
features = build_host_features(df)

publish_feature_table(
    name="airbnb.features.listing_features",
    primary_keys=["host_id"],
    df=features,
    description="Feature table com KPIs por host",
    tags={"domain": "airbnb", "granularity": "host", "team": "mentoria"},
)
```

---

## UV — Gerenciamento de Dependências

O projeto usa [UV](https://docs.astral.sh/uv/) como package manager, substituindo pip/pip-tools/poetry por uma ferramenta mais rápida e determinística.

### Comandos principais

```bash
# Sincronizar dependências (cria .venv automaticamente)
uv sync

# Incluir dependências de desenvolvimento
uv sync --extra dev

# Adicionar uma nova dependência
uv add <pacote>

# Adicionar dependência de dev
uv add --optional dev <pacote>

# Executar um script no ambiente virtual
uv run python script.py

# Executar pytest
uv run pytest
```

### Dependências do projeto

| Pacote                            | Propósito                          |
|-----------------------------------|------------------------------------|
| `databricks-connect>=18.0,<18.1` | SparkSession via serverless        |
| `databricks-sdk`                  | SDK do Databricks                  |
| `databricks-feature-engineering`  | Feature Store API                  |
| `python-dotenv`                   | Carregar variáveis do `.env`       |
| `pytest` (dev)                    | Testes                             |
| `ruff` (dev)                      | Linter e formatter                 |
| `ipykernel` (dev)                 | Kernel Jupyter para notebooks      |

---

## Notebooks

O notebook `notebooks/explore_listings.ipynb` realiza análise exploratória da tabela `airbnb.landing.listings` via Databricks Connect, incluindo:

- Schema e primeiras linhas
- Estatísticas descritivas das colunas numéricas
- Contagem de valores nulos por coluna
- Distribuição por `room_type`
- Top 10 bairros com mais listings
- Análise de superhosts vs não-superhosts
- Top 10 hosts com mais imóveis
- Disponibilidade média por tipo de quarto
- Médias dos scores de review

Para executar, abra o notebook no VS Code/Cursor e selecione o kernel `.venv (Python 3.12)`.

---

## Desenvolvimento

```bash
# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Testes
uv run pytest
```
