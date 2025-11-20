# bq_client.py
from google.cloud import bigquery
import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)
# directory = "//home//ubuntu//sql"
directory = ".//sql"
class BigQueryClient:
    def __init__(self, config):
        self.config = config
        self.client = bigquery.Client(
            project=config.BQ_PROJECT, 
            location=config.BQ_LOCATION
        )
                # ▼▼▼ NEW: LOAD BRAND MAPPING CSV AT STARTUP ▼▼▼
        try:
            mapping_path = f"{directory}//brand_mapping.csv"
            self.brand_mapping_df = pd.read_csv(mapping_path)
            # Ensure the 'brand' column is lowercase for consistent joining
            self.brand_mapping_df['brand'] = self.brand_mapping_df['brand'].str.upper()
            logger.info("Successfully loaded brand_mapping.csv")
        except FileNotFoundError:
            logger.error("FATAL: brand_mapping.csv not found! The bot may not function correctly.")
            self.brand_mapping_df = pd.DataFrame() # Create empty df to avoid errors
        
    async def execute_apf_query(self, target_country):
        apf_file = f"{directory}//apf_function.sql"
        with open(apf_file, "r", encoding="utf-8") as f:
            sql = f.read()
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("target_country", "STRING", target_country)
            ]
        )
        try:
            query_job = self.client.query(sql, job_config=job_config)
            result = query_job.result()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    # ▼ NEW: for /dist
    async def execute_dist_query(self, target_date: str, selected_country: str | None):
        """
        Distribution (channels by country) for an EXACT local date (Asia/Bangkok).
        Params:
        - target_date: 'YYYY-MM-DD'
        - selected_country: STRING or None
        """
        dist_file = f"{directory}//dist_function.sql"
        with open(dist_file, "r", encoding="utf-8") as f:
            sql = f.read()

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("target_date", "DATE", target_date),
                bigquery.ScalarQueryParameter("selected_country", "STRING", selected_country),
            ]
        )
        try:
            query_job = self.client.query(sql, job_config=job_config)
            result = query_job.result()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error executing /dist query: {e}")
            raise

    async def execute_dpf_query(self, target_country: str | None):
        """
        Deposit Performance (DPF): last 3 local days, capped at 'now'.
        Optional filter by country (TH/PH/BD/PK/ID) when target_country is provided.
        """
        dpf_file = f"{directory}//dpf_function.sql"
        with open(dpf_file, "r", encoding="utf-8") as f:
            sql = f.read()

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("target_country", "STRING", target_country),
            ]
        )
        try:
            query_job = self.client.query(sql, job_config=job_config)
            result = query_job.result()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error executing /dpf query: {e}")
            raise

    async def execute_pmh_query(self, target_date: str, selected_country: str | None) -> list[dict]:
        """
        Executes the Payment Health query for a specific date and optional country.
        """
        pmh_file = f"{directory}//pmh_function.sql"
        with open(pmh_file, "r", encoding="utf-8") as f:
            sql = f.read()

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("target_date", "DATE", target_date),
                bigquery.ScalarQueryParameter("selected_country", "STRING", selected_country),
            ]
        )
        try:
            query_job = self.client.query(sql, job_config=job_config)
            # results = [dict(row) for row in query_job.result()]
        
            df = query_job.to_dataframe()
            # print(df.head(5))
            # print(self.brand_mapping_df.head(5))
            df_final = df.merge(self.brand_mapping_df, how = "left")

            results = df_final.to_dict(orient='records')
            print(df_final.head(10))
            return results
        except Exception as e:
            # CORRECTED LOG MESSAGE
            logger.error(f"Error executing /pmh query: {e}")
            raise   
        
    # in bq_client.py
    async def execute_pmh_week_query(self, as_of_date: str, selected_country: str | None) -> list[dict]:
        week_file = f"{directory}//pmh_week_function.sql"
        with open(week_file, "r", encoding="utf-8") as f:
            sql = f.read()

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("as_of_date", "DATE", as_of_date),
                bigquery.ScalarQueryParameter("selected_country", "STRING", selected_country),
            ]
        )
        try:
            query_job = self.client.query(sql, job_config=job_config)
            df = query_job.to_dataframe()

            # keep your mapping behavior (brand upper)
            df["brand"] =  df["brand"].str.upper().str.strip()
            print(df.head(5))
            print(self.brand_mapping_df.head(5))
            df_final = df.merge(self.brand_mapping_df, how="left")

            print(df_final[df_final["group_name"].isna()]["brand"].unique())
            return df_final.to_dict(orient="records")
        except Exception as e:
            logger.error(f"Error executing /pmh_week query: {e}")
            raise