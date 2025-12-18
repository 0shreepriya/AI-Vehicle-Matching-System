# AI Vehicle Matching System 🚗

This project implements an AI-driven vehicle matching and dynamic pricing system.
It uses machine learning models to predict ETA and demand, and exposes all
functionalities through REST APIs built with FastAPI.

## Project Structure
- API.py : Main FastAPI backend file
- app.py : Alternative experimental backend implementation
- models/ : Trained ML models (LightGBM, XGBoost)
- frontend/ : Basic HTML, CSS, and JavaScript frontend

## Features
- ETA prediction using LightGBM
- Demand and surge prediction using XGBoost
- Vehicle availability updates
- Top-K vehicle recommendations
- REST APIs using FastAPI

## Tech Stack
- Python
- FastAPI
- LightGBM
- XGBoost
- HTML, CSS, JavaScript

## How to Run the Backend
1. Open terminal in the project folder
2. Run:
   uvicorn API:app --reload
3. Open browser and go to:
   http://127.0.0.1:8000/docs

## Notes
- Frontend is optional and provided for demonstration
- ML model files are included for academic purposes
