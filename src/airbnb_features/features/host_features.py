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
