from pyspark.sql import DataFrame

from airbnb_features.common.spark_session import get_spark


def read_listings() -> DataFrame:
    spark = get_spark()
    return spark.read.table("airbnb.landing.listings")
