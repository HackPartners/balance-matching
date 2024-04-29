# Import dependencies
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString
import geopandas as gpd
from shapely.ops import linemerge
from flask import jsonify
import functions_framework
from db import Database
from mileage import Mileage
from google.cloud import storage
import json

storage_client = storage.Client()
bucket = storage_client.get_bucket('hubble-elr-geojsons')


# Convert miles to meters
def miles_to_m(mileage: float) -> float:
    return mileage * 1609.34

# Find coordinates for each balance and save it as a Point
def find_coords(elr: str, meterage: float) -> Point:
    gdf = elr_gdf[elr_gdf["elr"] == elr].copy()
    point = gdf.geometry.interpolate(meterage/gdf.length.values[0], normalized=True).values[0]

    return point

def find_coords_sb(lat: float, long: float) -> Point:
    return Point(long, lat)



def get_closest_assets(sb_id: int, radius: int) -> list[int]:
    points_gdf = balances.copy()
    point = scan_balances[scan_balances["sb_id"] == sb_id].geometry.values[0]
    nearby_points = points_gdf[points_gdf.geometry.apply(lambda geom: geom.distance(point) <= radius)]

    return nearby_points["asset_number"].unique().tolist()


db = Database()



def process_elr_data():
    blob = bucket.blob('balance/elrs.geojson')
    elr_string = json.loads(blob.download_as_string())
    elr_gdf = gpd.GeoDataFrame.from_features(elr_string["features"])
    # elr_gdf = gpd.read_file("https://storage.cloud.google.com/hubble-elr-geojsons/balance/elrs.geojson")
    # Fuse ELRs into single lines and clean up columns
    elr_gdf["geometry"] = elr_gdf["geometry"].apply(linemerge)
    elr_gdf = elr_gdf[["ELR", "L_M_FROM", "L_M_TO", "geometry"]].copy()
    elr_gdf.rename(columns={"L_M_FROM":"from", "L_M_TO":"to", "ELR": "elr"}, inplace=True)
    elr_gdf.crs = "EPSG:27700"
    elr_gdf = elr_gdf[["elr", "geometry"]].copy()
    elr_gdf = gpd.GeoDataFrame(elr_gdf, crs="EPSG:27700")

    return elr_gdf

def process_assets(elr_gdf):
    # Load Raw Data
    assets = pd.read_csv('https://storage.cloud.google.com/hubble-elr-geojsons/balance/assets.csv')   
    # Make columns nice and remove unsuable rows
    assets = assets[["Asset Number", "ELR", "Asset Start Mileage", "Asset End Mileage"]]
    assets.rename(columns={"Asset Number": "asset_number", "Asset Start Mileage": "mileage_from", "Asset End Mileage": "mileage_to", "ELR": "elr"}, inplace=True)
    assets.dropna(subset=["mileage_from", "mileage_to"], inplace=True)
    assets.dropna(subset=["elr"], inplace=True)

    # Split assets into individual balances
    balances = pd.DataFrame()

    for i, row in assets.iterrows():
        balances = pd.concat([balances, pd.DataFrame({
            "asset_number": row["asset_number"],
            "elr": row["elr"],
            "from_to": "from",
            "mileage": Mileage(row["mileage_from"]).miles_decimal
        }, index=[0])], ignore_index=True)

        balances = pd.concat([balances, pd.DataFrame({
            "asset_number": row["asset_number"],
            "elr": row["elr"],
            "from_to": "to",
            "mileage": Mileage(row["mileage_to"]).miles_decimal
        }, index=[0])], ignore_index=True)



    balances["meterage"] = balances["mileage"].apply(miles_to_m)
    balances.drop(columns=["mileage"], inplace=True)
    balances["geometry"] = balances.apply(lambda x: find_coords(x["elr"], x["meterage"]), axis=1)
    balances.drop(columns=["meterage", "elr"], inplace=True)
    balances = gpd.GeoDataFrame(balances, crs="EPSG:27700")
    return balances



def process_scan_balances():
    scan_balances = db.load_scan_balances()
    
    # Remove useless columns and rows
    scan_balances = scan_balances[["id", "lat", "long"]].copy()
    scan_balances.rename(columns={"id": "sb_id"}, inplace=True)
    scan_balances.dropna(subset=["lat", "long"], inplace=True)
    scan_balances = scan_balances[scan_balances["lat"] != scan_balances["long"]].copy()

    scan_balances["geometry"] = scan_balances.apply(lambda x: find_coords_sb(x["lat"], x["long"]), axis=1)
    scan_balances.drop(columns=["lat", "long"], inplace=True)
    scan_balances = gpd.GeoDataFrame(scan_balances, crs="EPSG:4326")
    scan_balances.to_crs("EPSG:27700", inplace=True)

    return scan_balances




def find_matches():
    elr_gdf = process_elr_data()
    balances = process_assets(elr_gdf)
    scan_balances = process_scan_balances()
    scan_balances["balances"] = scan_balances.apply(lambda x: get_closest_assets(x["sb_id"], 100), axis=1)
    matches = scan_balances.to_dict("record")

    return matches




# Response Handler function
@functions_framework.http
def request_handler(request):
    """Request handler function, runs the main ELR , and returns output in a json format.
        Runs when request with SCAN ID is made to function.

    Args:
        request: HTTP post request

    Returns:
        json: JSON response of matching
    """

    content_type = request.headers["content-type"]

    if content_type == "application/json":
        request_json = request.get_json(silent=True)

    if "match" in request_json:
        match = request_json["match"]
    if match:
        matches = find_matches()

    if not matches:
        return jsonify(
            message="No matches found",
            category="error",
            data=[],
            status=500,
        )

    else:
        return jsonify(
            message=f"Asset matching complete",
            category="success",
            matches=matches,
            status=200,
        )


