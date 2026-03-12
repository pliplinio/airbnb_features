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
