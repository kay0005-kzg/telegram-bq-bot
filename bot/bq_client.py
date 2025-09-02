# bq_client.py
from google.cloud import bigquery
import logging
import os

logger = logging.getLogger(__name__)

class BigQueryClient:
    def __init__(self, config):
        self.config = config
        self.client = bigquery.Client(
            project=config.BQ_PROJECT, 
            location=config.BQ_LOCATION
        )
        
    async def execute_apf_query(self, target_country):
        apf_file = ".//sql//apf_function.sql"
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
        dist_file = ".//sql//dist_function.sql"
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
        dpf_file = ".//sql//dpf_function.sql"
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
