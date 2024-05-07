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
from tqdm import tqdm
storage_client = storage.Client()
bucket = storage_client.get_bucket('hubble-elr-geojsons')
tqdm.pandas()

# Convert miles to meters
def miles_to_m(mileage: float) -> float:
    return mileage * 1609.34


# Find coordinates for each balance and save it as a Point
def find_coords(elr: str, meterage: float, elr_gdf) -> Point:
    gdf = elr_gdf[elr_gdf["elr"] == elr].copy()
    point = gdf.geometry.interpolate(meterage / gdf.length.values[0], normalized=True).values[0]

    return point


def find_coords_sb(lat: float, long: float) -> Point:
    return Point(long, lat)


def get_closest_assets(sb_id: int, radius: int, balances, scan_balances) -> list[int]:
    points_gdf = balances.copy()
    point = scan_balances[scan_balances["sb_id"] == sb_id].geometry.values[0]
    nearby_points = points_gdf[points_gdf.geometry.apply(lambda geom: geom.distance(point) <= radius)]


    return nearby_points["balance_id"].unique().tolist()


db = Database()


def process_elr_data():
    print('loading elr data')
    blob = bucket.blob('balance/elrs.geojson')
    elr_string = json.loads(blob.download_as_string())
    elr_gdf = gpd.GeoDataFrame.from_features(elr_string["features"])
    print('loaded elr data')
    # Fuse ELRs into single lines and clean up columns
    elr_gdf["geometry"] = elr_gdf["geometry"].apply(linemerge)
    elr_gdf = elr_gdf[["ELR", "L_M_FROM", "L_M_TO", "geometry"]].copy()
    elr_gdf.rename(columns={"L_M_FROM": "from", "L_M_TO": "to", "ELR": "elr"}, inplace=True)
    elr_gdf.crs = "EPSG:27700"
    elr_gdf = elr_gdf[["elr", "geometry"]].copy()
    elr_gdf = gpd.GeoDataFrame(elr_gdf, crs="EPSG:27700")

    return elr_gdf


def process_assets(elr_gdf):
    # Load Raw Data
    assets = db.load_balances()

    # Make columns nice and remove unsuable rows
    assets = assets[["id", "asset_number", "from_location", "to_location"]]
    assets.rename(columns={"id": "balance_id"}, inplace=True)


    # Split assets into individual balances
    balances = pd.DataFrame()

    for i, row in assets.iterrows():
        
        start = pd.DataFrame(row["from_location"], index=[0])
        end = pd.DataFrame(row["to_location"], index=[0])

        
                                         
                                         
        balances = pd.concat([balances, pd.DataFrame({
            "balance_id": row["balance_id"],
            "asset_id": row['asset_number'],
            "elr": start.elr,
            "from_to": "from",
            "mileage": Mileage(start['mileage'][0]).miles_decimal
        }, index=[0])], ignore_index=True)

        balances = pd.concat([balances, pd.DataFrame({
            "balance_id": row["balance_id"],
            "asset_id": row['asset_number'],
            "elr": end.elr,
            "from_to": "to",
            "mileage": Mileage(end['mileage'][0]).miles_decimal
        }, index=[0])], ignore_index=True)

    balances["meterage"] = balances["mileage"].apply(miles_to_m)
    balances.drop(columns=["mileage"], inplace=True)
    balances["geometry"] = balances.apply(lambda x: find_coords(x["elr"], x["meterage"], elr_gdf), axis=1)
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
    print(balances['geometry'])
    scan_balances = process_scan_balances()
    print(balances['geometry'])
    scan_balances["balances"] = scan_balances.progress_apply(lambda x: get_closest_assets(x["sb_id"], 100, balances, scan_balances), axis=1)
    scan_balances = scan_balances[["sb_id", "balances"]]
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
