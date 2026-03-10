# Databricks notebook source
# DBTITLE 1,Cell 1

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType
from datetime import date

df_listings = spark.read.table("airbnb.landing.listings")
REFERENCE_DATE = F.lit(date.today())

host_features = (
    df_listings
    .dropna(subset=["host_id"])
    .groupBy("host_id")
    .agg(
        F.count("id").alias("total_listings"),
        F.sum("number_of_reviews").alias("total_reviews"),
        
         F.sum("number_of_reviews_ltm").alias("total_reviews_last_12m"),
    #     F.avg("price_clean").alias("avg_price"),
    #     F.min("price_clean").alias("min_price"),
    #     F.max("price_clean").alias("max_price"),
    #     F.stddev("price_clean").alias("stddev_price"),
    #     F.sum(F.col("price_clean") * F.col("number_of_reviews")).alias("total_estimated_revenue"),
    #     F.avg("review_scores_rating").alias("avg_review_score"),
    #     F.avg("review_scores_cleanliness").alias("avg_cleanliness_score"),
    #     F.avg("review_scores_communication").alias("avg_communication_score"),
    #     F.avg("review_scores_value").alias("avg_value_score"),
    #     F.max(F.when(F.col("host_is_superhost") == "t", 1).otherwise(0)).alias("is_superhost"),
    #     F.min("host_since").alias("host_since"),
    #     F.avg("reviews_per_month").alias("avg_reviews_per_month"),
    #     F.max("last_review").alias("last_review_date"),
    #     F.countDistinct("room_type").alias("listing_type_diversity"),
    #     F.countDistinct("neighbourhood").alias("neighbourhood_diversity"),
    #     F.avg("availability_365").alias("avg_availability_365"),
    #     F.avg("availability_30").alias("avg_availability_30"),
    #     F.sum("accommodates").alias("total_accommodates"),
    #     F.avg("accommodates").alias("avg_accommodates"),
    #     F.first(
    #         F.regexp_replace(F.col("host_response_rate"), "%", "").cast(DoubleType())
    #     ).alias("host_response_rate_pct"),
    # )
    # .withColumn("host_tenure_days", F.datediff(REFERENCE_DATE, F.col("host_since")))
    # .withColumn("days_since_last_review", F.datediff(REFERENCE_DATE, F.col("last_review_date")))
    # .withColumn(
    #     "revenue_per_listing",
    #     F.when(F.col("total_listings") > 0, F.col("total_estimated_revenue") / F.col("total_listings")).otherwise(0)
    # )
    # .withColumn(
    #     "reviews_per_listing",
    #     F.when(F.col("total_listings") > 0, F.col("total_reviews") / F.col("total_listings")).otherwise(0)
    )
)

# COMMAND ----------

from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup
fe = FeatureEngineeringClient()  # Ensure this class is defined or imported if used

# COMMAND ----------

fe.create_table(
    name="airbnb.features.listing_features",
    primary_keys=["host_id"],
    df=host_features,
    description=(
        "Feature table com KPIs por listing (imóvel). "
        "Inclui métricas de preço, ocupação, qualidade, competitividade no bairro, "
        "e score composto de qualidade. "
        "Analogia: cada listing = conta/produto de um banco."
    ),
    tags={
        "domain": "airbnb",
        "granularity": "listing",
        "source": "bronze_listings,bronze_calendar",
        "team": "mentoria",
        "refresh_cadence": "daily",
    },
)

# COMMAND ----------

# MAGIC %md
# MAGIC #iii
# MAGIC
