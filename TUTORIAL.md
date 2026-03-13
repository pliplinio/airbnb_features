# Tutorial: Construindo uma Feature Store no Databricks com desenvolvimento local

Este tutorial guia você passo a passo na criação de um projeto Python para construção de Feature Tables no Databricks Unity Catalog, usando **UV** para gerenciar dependências e **Databricks Connect (serverless)** para executar PySpark direto do seu editor local (VS Code / Cursor).

---

## Sumário

1. [O que vamos construir](#1-o-que-vamos-construir)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Instalar o UV](#3-instalar-o-uv)
4. [Criar o projeto](#4-criar-o-projeto)
5. [Configurar o pyproject.toml](#5-configurar-o-pyprojecttoml)
6. [Estrutura de pastas](#6-estrutura-de-pastas)
7. [Configurar o Databricks Connect (serverless)](#7-configurar-o-databricks-connect-serverless)
8. [Instalar dependências](#8-instalar-dependências)
9. [Criar o módulo de conexão](#9-criar-o-módulo-de-conexão)
10. [Testar a conexão](#10-testar-a-conexão)
11. [Criar o módulo de ingestão (landing)](#11-criar-o-módulo-de-ingestão-landing)
12. [Criar o módulo de features](#12-criar-o-módulo-de-features)
13. [Criar o módulo de publicação (Feature Store)](#13-criar-o-módulo-de-publicação-feature-store)
14. [Pipeline completo: da ingestão à publicação](#14-pipeline-completo-da-ingestão-à-publicação)
15. [Criar notebook de exploração](#15-criar-notebook-de-exploração)
16. [Versionamento com Git](#16-versionamento-com-git)
17. [Conceitos-chave explicados](#17-conceitos-chave-explicados)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. O que vamos construir

Um projeto que:

- Conecta ao **Databricks** direto do seu computador local (sem precisar abrir notebooks no browser)
- Lê dados brutos da tabela `airbnb.landing.listings` no Unity Catalog
- Transforma esses dados em **features** agregadas por host
- Publica as features como uma **Feature Table** no Databricks Feature Store
- Usa **UV** para gerenciar pacotes Python de forma rápida e reproduzível

```
  Sua máquina local                          Databricks (nuvem)
┌─────────────────────┐                  ┌──────────────────────────┐
│  VS Code / Cursor   │  ── Databricks ──│  Serverless Compute      │
│  Código PySpark     │     Connect      │  Unity Catalog           │
│  UV + .venv         │                  │  airbnb.landing.listings │
└─────────────────────┘                  │  airbnb.features.*       │
                                         └──────────────────────────┘
```

---

## 2. Pré-requisitos

| Requisito | Como verificar | Como instalar |
|-----------|---------------|---------------|
| **Python 3.12+** | `python --version` | [python.org](https://www.python.org/downloads/) |
| **Git** | `git --version` | [git-scm.com](https://git-scm.com/) |
| **VS Code ou Cursor** | — | [code.visualstudio.com](https://code.visualstudio.com/) / [cursor.com](https://cursor.com/) |
| **Conta Databricks** | Acesse seu workspace | Solicite ao admin |
| **Personal Access Token** | Settings > Developer > Access Tokens | Gere no workspace |

### Como gerar um Personal Access Token (PAT) no Databricks

1. Acesse seu workspace (ex: `https://dbc-XXXXX.cloud.databricks.com/`)
2. Clique no seu avatar (canto superior direito) > **Settings**
3. Vá em **Developer** > **Access tokens**
4. Clique em **Generate new token**
5. Dê um nome (ex: `databricks-connect-local`) e defina a expiração
6. Copie o token gerado (começa com `dapi...`)

---

## 3. Instalar o UV

O [UV](https://docs.astral.sh/uv/) é um package manager para Python criado pela Astral (mesmos criadores do Ruff). Ele substitui pip, pip-tools, poetry e virtualenv com uma ferramenta única e muito mais rápida.

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux / macOS:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Após instalar, adicione ao PATH se necessário e verifique:

```bash
uv --version
# uv 0.10.9 (ou superior)
```

---

## 4. Criar o projeto

```bash
# Crie o diretório e inicialize o Git
mkdir airbnb_features
cd airbnb_features
git init
```

---

## 5. Configurar o pyproject.toml

Crie o arquivo `pyproject.toml` na raiz. Este é o arquivo central do projeto — define metadados, dependências e configurações de ferramentas.

```toml
[project]
name = "airbnb-features"
version = "0.1.0"
description = "Feature Store para dados Airbnb no Databricks"
requires-python = ">=3.12"
dependencies = [
    "databricks-connect>=18.0,<18.1",
    "databricks-sdk",
    "databricks-feature-engineering",
    "python-dotenv",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "ruff",
    "ipykernel",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/airbnb_features"]

[tool.ruff]
line-length = 120

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Por que cada dependência:**

| Pacote | Para quê |
|--------|----------|
| `databricks-connect>=18.0,<18.1` | Conectar ao Databricks serverless (18.1+ não suporta serverless) |
| `databricks-sdk` | SDK oficial do Databricks |
| `databricks-feature-engineering` | API do Feature Store |
| `python-dotenv` | Carregar variáveis do `.env` sem expor credenciais |
| `pytest` | Rodar testes |
| `ruff` | Linter + formatter (rápido, feito em Rust) |
| `ipykernel` | Executar notebooks Jupyter no VS Code/Cursor |

Crie também o arquivo `.python-version`:

```
3.12
```

---

## 6. Estrutura de pastas

Crie a seguinte árvore de diretórios:

```bash
# No Windows (PowerShell)
mkdir src/airbnb_features/common
mkdir src/airbnb_features/landing
mkdir src/airbnb_features/features
mkdir src/airbnb_features/utils
mkdir tests
mkdir notebooks
```

Crie os arquivos `__init__.py` em cada pacote Python (podem ser vazios):

```
src/airbnb_features/__init__.py
src/airbnb_features/common/__init__.py
src/airbnb_features/landing/__init__.py
src/airbnb_features/features/__init__.py
src/airbnb_features/utils/__init__.py
tests/__init__.py
```

A estrutura final deve ficar assim:

```
airbnb_features/
├── src/
│   └── airbnb_features/          # Pacote Python principal
│       ├── __init__.py
│       ├── common/               # Código compartilhado
│       │   ├── __init__.py
│       │   └── spark_session.py
│       ├── landing/              # Ingestão de dados brutos
│       │   ├── __init__.py
│       │   └── ingest_listings.py
│       ├── features/             # Construção de features
│       │   ├── __init__.py
│       │   └── host_features.py
│       └── utils/                # Utilitários
│           ├── __init__.py
│           └── feature_store.py
├── tests/
├── notebooks/
├── .databricks/
│   └── profile.json
├── pyproject.toml
├── .python-version
├── .env                          # NÃO versionar
└── .gitignore
```

**Mapeamento das camadas para o Unity Catalog:**

| Pasta do projeto | Schema no Unity Catalog | Papel |
|-----------------|------------------------|-------|
| `landing/` | `airbnb.landing` | Dados brutos ingeridos |
| `features/` | `airbnb.features` | Feature tables calculadas |

---

## 7. Configurar o Databricks Connect (serverless)

### 7.1 Arquivo `.env`

Crie o arquivo `.env` na raiz do projeto com suas credenciais:

```env
DATABRICKS_HOST=https://dbc-XXXXX.cloud.databricks.com/
DATABRICKS_TOKEN=dapi_seu_token_aqui
```

> **Importante:** não é necessário `CLUSTER_ID` porque usamos **serverless compute**. O Databricks provisiona recursos automaticamente.

### 7.2 Arquivo `.databricks/profile.json`

```json
{
  "host": "https://dbc-XXXXX.cloud.databricks.com/",
  "serverless": true
}
```

### 7.3 Arquivo `.gitignore`

Proteja suas credenciais e arquivos gerados:

```gitignore
desktop.ini
__pycache__/
*.pyc
.env
.venv/
*.egg-info/
dist/
build/
.databricks/.bundle/
.ruff_cache/
.pytest_cache/
```

---

## 8. Instalar dependências

```bash
# Instala produção + dev, cria .venv automaticamente
uv sync --extra dev
```

O UV vai:
1. Resolver todas as dependências e criar o `uv.lock`
2. Criar um `.venv/` na raiz do projeto
3. Instalar todos os pacotes (157 pacotes neste projeto)

---

## 9. Criar o módulo de conexão

Crie `src/airbnb_features/common/spark_session.py`:

```python
from databricks.connect import DatabricksSession
from dotenv import load_dotenv
import os

load_dotenv()


def get_spark() -> DatabricksSession:
    return (
        DatabricksSession.builder
        .host(os.getenv("DATABRICKS_HOST", "https://dbc-XXXXX.cloud.databricks.com/"))
        .token(os.getenv("DATABRICKS_TOKEN"))
        .serverless(True)
        .getOrCreate()
    )
```

**O que este código faz:**

1. `load_dotenv()` — carrega as variáveis do arquivo `.env`
2. `DatabricksSession.builder` — cria um builder para a sessão Spark
3. `.host(...)` — aponta para seu workspace Databricks
4. `.token(...)` — autentica com seu PAT
5. `.serverless(True)` — usa serverless compute (sem cluster dedicado)
6. `.getOrCreate()` — reutiliza a sessão se já existir

---

## 10. Testar a conexão

Execute o comando abaixo para verificar se tudo está funcionando:

```bash
uv run python -c "from airbnb_features.common.spark_session import get_spark; spark = get_spark(); spark.sql('SELECT 1 as test').show()"
```

Se a conexão estiver correta, você verá:

```
+----+
|test|
+----+
|   1|
+----+
```

> A primeira execução pode demorar alguns segundos enquanto o serverless provisiona os recursos.

---

## 11. Criar o módulo de ingestão (landing)

Crie `src/airbnb_features/landing/ingest_listings.py`:

```python
from pyspark.sql import DataFrame

from airbnb_features.common.spark_session import get_spark


def read_listings() -> DataFrame:
    spark = get_spark()
    return spark.read.table("airbnb.landing.listings")
```

Este módulo encapsula a leitura da tabela de origem. Qualquer outro módulo que precise dos dados de listings importa esta função em vez de acessar a tabela diretamente.

---

## 12. Criar o módulo de features

Crie `src/airbnb_features/features/host_features.py`:

```python
from pyspark.sql import DataFrame, functions as F
from datetime import date

REFERENCE_DATE = F.lit(date.today())


def build_host_features(df_listings: DataFrame) -> DataFrame:
    return (
        df_listings
        .dropna(subset=["host_id"])
        .groupBy("host_id")
        .agg(
            F.count("id").alias("total_listings"),
            F.sum("number_of_reviews").alias("total_reviews"),
            F.sum("number_of_reviews_ltm").alias("total_reviews_last_12m"),
        )
    )
```

**O que esta transformação faz:**

1. Remove linhas sem `host_id`
2. Agrupa por `host_id` (cada host pode ter vários imóveis)
3. Calcula para cada host:
   - **total_listings** — quantos imóveis possui
   - **total_reviews** — soma de reviews de todos os imóveis
   - **total_reviews_last_12m** — reviews dos últimos 12 meses

A função recebe e retorna um DataFrame, seguindo o padrão funcional que facilita testes e composição.

---

## 13. Criar o módulo de publicação (Feature Store)

Crie `src/airbnb_features/utils/feature_store.py`:

```python
from databricks.feature_engineering import FeatureEngineeringClient
from pyspark.sql import DataFrame


def publish_feature_table(
    name: str,
    primary_keys: list[str],
    df: DataFrame,
    description: str,
    tags: dict[str, str] | None = None,
):
    fe = FeatureEngineeringClient()
    fe.create_table(
        name=name,
        primary_keys=primary_keys,
        df=df,
        description=description,
        tags=tags or {},
    )
```

**O que este código faz:**

1. Cria um cliente do Feature Engineering
2. Publica o DataFrame como uma **Feature Table** no Unity Catalog
3. Registra metadados (description, tags) para governança

Após a publicação, a feature table aparece em:
- **Unity Catalog** > `airbnb` > `features` > `listing_features`
- **Feature Store UI** do Databricks

---

## 14. Pipeline completo: da ingestão à publicação

Com todos os módulos prontos, o pipeline completo fica assim:

```python
from airbnb_features.landing.ingest_listings import read_listings
from airbnb_features.features.host_features import build_host_features
from airbnb_features.utils.feature_store import publish_feature_table

# 1. Ler dados brutos
df = read_listings()

# 2. Construir features
features = build_host_features(df)

# 3. Publicar no Feature Store
publish_feature_table(
    name="airbnb.features.listing_features",
    primary_keys=["host_id"],
    df=features,
    description="Feature table com KPIs por host do Airbnb",
    tags={
        "domain": "airbnb",
        "granularity": "host",
        "source": "airbnb.landing.listings",
        "team": "mentoria",
        "refresh_cadence": "daily",
    },
)
```

Execute com:

```bash
uv run python -c "
from airbnb_features.landing.ingest_listings import read_listings
from airbnb_features.features.host_features import build_host_features
features = build_host_features(read_listings())
features.show(10)
"
```

---

## 15. Criar notebook de exploração

Crie o notebook `notebooks/explore_listings.ipynb` no VS Code/Cursor (New File > Jupyter Notebook) e adicione células para explorar os dados:

**Célula 1 — Setup e leitura:**

```python
from airbnb_features.common.spark_session import get_spark
from pyspark.sql import functions as F

spark = get_spark()
df = spark.read.table("airbnb.landing.listings")
print(f"Total de registros: {df.count()}")
```

**Célula 2 — Schema:**

```python
df.printSchema()
```

**Célula 3 — Valores nulos:**

```python
null_counts = df.select([
    F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c)
    for c in df.columns
])
null_counts.show(truncate=False)
```

**Célula 4 — Distribuição por room_type:**

```python
df.groupBy("room_type").agg(
    F.count("id").alias("total_listings"),
    F.avg("number_of_reviews").alias("avg_reviews"),
).orderBy(F.desc("total_listings")).show()
```

**Célula 5 — Top 10 bairros:**

```python
df.groupBy("neighbourhood").agg(
    F.count("id").alias("total_listings"),
    F.avg("number_of_reviews").alias("avg_reviews"),
    F.avg("availability_365").alias("avg_availability_365"),
).orderBy(F.desc("total_listings")).show(10)
```

> Selecione o kernel `.venv (Python 3.12)` no canto superior direito do notebook para executar.

---

## 16. Versionamento com Git

```bash
# Adicionar todos os arquivos (o .env será ignorado pelo .gitignore)
git add .

# Commit
git commit -m "Add project structure with UV, Databricks Connect serverless, and feature store scaffolding"

# Adicionar remote e push
git remote add origin https://github.com/seu-usuario/airbnb_features.git
git push -u origin main
```

---

## 17. Conceitos-chave explicados

### UV vs pip vs poetry

| Aspecto | pip | poetry | UV |
|---------|-----|--------|----|
| Velocidade | Lento | Médio | Muito rápido (Rust) |
| Lock file | Não tem | `poetry.lock` | `uv.lock` |
| Venv automático | Não | Sim | Sim |
| Resolução determinística | Não | Sim | Sim |
| Arquivo de config | `requirements.txt` | `pyproject.toml` | `pyproject.toml` |

### Databricks Connect vs Notebooks no browser

| Aspecto | Notebooks (browser) | Databricks Connect (local) |
|---------|---------------------|---------------------------|
| Onde você escreve código | UI do Databricks | VS Code, Cursor, PyCharm |
| Onde o código executa | Cluster/Serverless | Cluster/Serverless |
| Git integration | Limitado | Nativo |
| Autocomplete/Linting | Básico | Completo (IDE) |
| Debugging | Print | Breakpoints, debugger |
| Testes unitários | Difícil | pytest nativo |

### Serverless vs Cluster dedicado

| Aspecto | Cluster dedicado | Serverless |
|---------|-----------------|------------|
| Startup | 3-10 min | Segundos |
| Custo quando ocioso | Sim (se não auto-terminar) | Não |
| Configuração | `cluster_id` necessário | Apenas `serverless: true` |
| Escala | Manual | Automática |
| Versão databricks-connect | Qualquer | `>=18.0,<18.1` |

### Feature Store — Por que usar?

O Feature Store do Databricks resolve problemas comuns em ML:

- **Reutilização**: features calculadas uma vez, usadas por vários modelos
- **Consistência**: mesma lógica de features no treino e na inferência
- **Descoberta**: engenheiros encontram features existentes via catálogo
- **Linhagem**: rastreabilidade de onde cada feature vem
- **Governança**: tags, descrições e controle de acesso via Unity Catalog

---

## 18. Troubleshooting

### Erro: "databricks-connect is unsupported with serverless"

**Causa:** versão do `databricks-connect` acima de 18.0.x.

**Solução:** fixe a versão no `pyproject.toml`:

```toml
"databricks-connect>=18.0,<18.1"
```

Depois rode `uv sync`.

### Erro: "DATABRICKS_TOKEN not set"

**Causa:** arquivo `.env` não existe ou não tem o token.

**Solução:** crie o `.env` com:

```env
DATABRICKS_HOST=https://dbc-XXXXX.cloud.databricks.com/
DATABRICKS_TOKEN=dapi_seu_token_aqui
```

### Erro: "Table or view not found: airbnb.landing.listings"

**Causa:** a tabela não existe no Unity Catalog do seu workspace.

**Solução:** verifique no Databricks UI se o catalog `airbnb`, schema `landing` e tabela `listings` existem.

### UV não reconhecido como comando

**Causa:** UV não está no PATH.

**Solução (PowerShell):**

```powershell
$env:Path = "C:\Users\SEU_USUARIO\.local\bin;$env:Path"
```

Ou reinicie o terminal após a instalação.

### Notebook não encontra o módulo `airbnb_features`

**Causa:** o kernel do notebook não está usando o `.venv` do projeto.

**Solução:** no VS Code/Cursor, clique no seletor de kernel (canto superior direito do notebook) e selecione `.venv (Python 3.12)`.
