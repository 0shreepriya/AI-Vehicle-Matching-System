from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import joblib
import numpy as np
from geopy.distance import geodesic


eta_model = joblib.load("models/lightgbm_eta_model.pkl")
demand_model = joblib.load("models/xgboost_demand_model.pkl")

app = FastAPI(title="AI-Driven Vehicle Matching & Dynamic Pricing ")



vehicles_db = pd.DataFrame(columns=[
    "vehicle_id",
    "lat",
    "lng",
    "vehicle_type",
    "driver_rating",
    "available"
])


class VehicleUpdate(BaseModel):
    vehicle_id: str
    lat: float
    lng: float
    vehicle_type: str
    driver_rating: float
    available: bool


class RideRequest(BaseModel):
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    hour: int
    day_of_week: int
    is_weekend: int
    is_peak: int
    user_preference: str = "balanced"



def calculate_distance(lat1, lng1, lat2, lng2):
    return geodesic((lat1, lng1), (lat2, lng2)).km


def dynamic_pricing(distance_km, eta_min, demand, supply):
    base_fare = 30
    per_km = 8
    per_min = 2

    surge = 1 + max(0, (demand / max(supply, 1) - 1) * 0.5)
    price = (base_fare + per_km * distance_km + per_min * eta_min) * surge

    return round(price, 2), round(surge, 2)


def rank_vehicles(df, price, preference):
    if preference == "fastest":
        w_eta, w_price, w_rating = 0.6, 0.2, 0.2
    elif preference == "cheapest":
        w_eta, w_price, w_rating = 0.2, 0.6, 0.2
    else:  # balanced
        w_eta, w_price, w_rating = 0.4, 0.4, 0.2

    df = df.copy()
    df["score"] = (
        -w_eta * df["pickup_eta"]
        -w_price * price / 100
        +w_rating * df["driver_rating"]
    )

    return df.sort_values("score", ascending=False)




@app.post("/vehicles/update")
def update_vehicle(data: VehicleUpdate):
    global vehicles_db

    # Remove existing vehicle if present
    vehicles_db = vehicles_db[vehicles_db.vehicle_id != data.vehicle_id]

    # Add updated vehicle
    vehicles_db = pd.concat(
        [vehicles_db, pd.DataFrame([data.dict()])],
        ignore_index=True
    )

    return {"message": "Vehicle updated successfully"}



@app.post("/ride/quote")
def get_ride_quote(req: RideRequest, top_k: int = 3):
    available = vehicles_db[vehicles_db.available == True].copy()

    if available.empty:
        return {"message": "No vehicles available"}

    # Pickup ETA (vehicle → rider)
    available["pickup_eta"] = available.apply(
        lambda r: calculate_distance(
            req.pickup_lat, req.pickup_lng, r.lat, r.lng
        ) * 2,   # simple speed assumption
        axis=1
    )

    # Trip distance (rider → destination)
    trip_distance = calculate_distance(
        req.pickup_lat, req.pickup_lng,
        req.drop_lat, req.drop_lng
    )

    # ETA prediction (LightGBM)
    X_eta = [[
        trip_distance,
        trip_distance,
        req.hour,
        req.day_of_week,
        req.is_weekend,
        req.is_peak
    ]]
    eta = float(eta_model.predict(X_eta)[0])

    # Demand prediction (XGBoost)
    X_demand = [[req.hour, req.day_of_week, req.is_peak]]
    demand = max(1, int(demand_model.predict(X_demand)[0]))
    supply = len(available)

    # Pricing
    price, surge = dynamic_pricing(trip_distance, eta, demand, supply)

    # Vehicle ranking
    ranked = rank_vehicles(available, price, req.user_preference)

    return {
        "predicted_eta_min": round(eta, 2),
        "trip_distance_km": round(trip_distance, 2),
        "price": price,
        "surge_multiplier": surge,
        "recommended_vehicles": ranked.head(top_k).to_dict(orient="records")
    }







from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import math

app = FastAPI(title="AI Vehicle Matching API")


vehicles_db = {}


def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine distance (km)"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c



class VehicleUpdate(BaseModel):
    vehicle_id: str
    latitude: float
    longitude: float
    available: bool
    category: str  # Mini, Sedan, SUV


@app.post("/vehicles/update")
def update_vehicle(vehicle: VehicleUpdate):
    vehicles_db[vehicle.vehicle_id] = vehicle.dict()
    return {
        "message": "Vehicle updated successfully",
        "vehicle": vehicles_db[vehicle.vehicle_id]
    }




class RideRequest(BaseModel):
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    top_k: int = 3


@app.post("/ride/quote")
def get_ride_quote(ride: RideRequest):
    results = []

    for v in vehicles_db.values():
        if not v["available"]:
            continue

        distance = calculate_distance(
            ride.pickup_lat,
            ride.pickup_lng,
            v["latitude"],
            v["longitude"]
        )

        # 🔮 ETA logic (placeholder for ML model)
        eta_minutes = round(distance * 4, 2)

        # 💰 Cost logic
        base_fare = 40
        cost = round(base_fare + distance * 15, 2)

        results.append({
            "vehicle_id": v["vehicle_id"],
            "category": v["category"],
            "distance_km": round(distance, 2),
            "eta_minutes": eta_minutes,
            "estimated_cost": cost
        })

    # Sort by ETA
    results = sorted(results, key=lambda x: x["eta_minutes"])

    return {
        "recommended_vehicles": results[:ride.top_k]
    }



def root():
    return {"status": "Vehicle Matching API is running"}





