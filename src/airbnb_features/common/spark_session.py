from databricks.connect import DatabricksSession
from dotenv import load_dotenv
import os

load_dotenv()


def get_spark() -> DatabricksSession:
    return (
        DatabricksSession.builder
        .host(os.getenv("DATABRICKS_HOST", "https://dbc-704623d7-21a0.cloud.databricks.com/"))
        .token(os.getenv("DATABRICKS_TOKEN"))
        .serverless(True)
        .getOrCreate()
    )
