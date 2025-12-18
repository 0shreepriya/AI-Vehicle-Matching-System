from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import math
import requests
from datetime import datetime
from typing import Dict


app = FastAPI(title="AI Vehicle Matching System")


eta_model = joblib.load("models/lightgbm_eta_model.pkl")       # LightGBM ETA model
demand_model = joblib.load("models/xgboost_demand_model.pkl")  # Demand / surge model


vehicles_db: Dict[str, dict] = {}


class VehicleUpdate(BaseModel):
    vehicle_id: str
    latitude: float
    longitude: float
    available: bool
    category: str   # Mini / Sedan / SUV


class RideRequest(BaseModel):
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    traffic_level: int = 1
    top_k: int = 3



def get_osm_distance_duration(lat1, lon1, lat2, lon2):
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=false"
    )
    response = requests.get(url, timeout=5)
    data = response.json()

    if "routes" not in data:
        return None, None

    distance_km = data["routes"][0]["distance"] / 1000
    duration_min = data["routes"][0]["duration"] / 60
    return distance_km, duration_min



def build_eta_features(distance_km, traffic_level):
    now = datetime.now()
    hour = now.hour
    day_of_week = now.weekday()
    is_peak_hour = 1 if hour in [8, 9, 10, 17, 18, 19] else 0
    demand_index = 1 if traffic_level >= 2 else 0

    return [[
        distance_km,
        traffic_level,
        hour,
        day_of_week,
        is_peak_hour,
        demand_index
    ]]


def build_demand_features(distance_km, traffic_level):
    now = datetime.now()
    hour = now.hour
    day_of_week = now.weekday()
    is_peak_hour = 1 if hour in [8, 9, 10, 17, 18, 19] else 0
    demand_index = 1 if traffic_level >= 2 else 0

    return [[
        distance_km,
        traffic_level,
        hour,
        day_of_week,
        is_peak_hour,
        demand_index
    ]]



@app.get("/")
def root():
    return {"status": "API running successfully"}



@app.post("/vehicles/update")
def update_vehicle(vehicle: VehicleUpdate):
    vehicles_db[vehicle.vehicle_id] = vehicle.dict()
    return {
        "message": "Vehicle updated successfully",
        "vehicle": vehicles_db[vehicle.vehicle_id]
    }



@app.post("/ride/quote")
def get_ride_quote(ride: RideRequest):

    recommendations = []

    for v in vehicles_db.values():
        if not v["available"]:
            continue

        # Real road distance & base ETA from OSM
        distance_km, route_eta = get_osm_distance_duration(
            ride.pickup_lat,
            ride.pickup_lng,
            v["latitude"],
            v["longitude"]
        )

        if distance_km is None:
            continue

        # ---------- ETA ML MODEL ----------
        eta_features = build_eta_features(distance_km, ride.traffic_level)
        ml_eta = eta_model.predict(eta_features)[0]

        # Hybrid ETA (OSM + ML)
        final_eta = 0.6 * route_eta + 0.4 * ml_eta

        # ---------- DEMAND ML MODEL ----------
        demand_features = build_demand_features(distance_km, ride.traffic_level)
        demand = demand_model.predict(demand_features)[0]

        # ---------- PRICING ----------
        base_fare = 40
        per_km_rate = 15
        surge = 1.5 if demand == 1 else 1.0

        cost = base_fare + (distance_km * per_km_rate * surge)

        recommendations.append({
            "vehicle_id": v["vehicle_id"],
            "category": v["category"],
            "distance_km": round(distance_km, 2),
            "eta_minutes": round(float(final_eta), 2),
            "estimated_cost": round(cost, 2)
        })

    # Sort by ETA (best vehicles first)
    recommendations.sort(key=lambda x: x["eta_minutes"])

    return {
        "recommended_vehicles": recommendations[:ride.top_k]
    }
