# Imports
import psycopg2.pool
import pandas as pd
import os
import logging
import geopandas as gpd
from google.cloud import storage
from shapely import wkt
from google.cloud import storage
import json


class Database:
    def __init__(self):
        self.host = os.environ["CLOUDSQL_HOST"]
        self.database = os.environ["CLOUDSQL_DATABASE"]
        self.port = os.environ["CLOUDSQL_PORT"]
        self.user = os.environ["CLOUDSQL_USER"]
        self.password = os.environ["CLOUDSQL_PASSWORD"]

    def load_scan_balances(self):
        pool = psycopg2.pool.SimpleConnectionPool(
            5,
            30,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

        connection1 = pool.getconn()

        # Use the connection to execute a query
        cursor = connection1.cursor()
        query = f"""SELECT sb.* FROM scan_balances sb JOIN route_track rt ON rt.track_id = sb.track_id 
        JOIN routes r ON r.id = rt.route_id
        JOIN client_lines cl ON r.line_id = cl.line_id
        WHERE cl.client_id = 11;"""
        cursor.execute(query)
        table_colnames = [desc[0] for desc in cursor.description]
        df_scan_balances = pd.DataFrame(cursor.fetchall(), columns=table_colnames)
        connection1.close()


        return df_scan_balances
