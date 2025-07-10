from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import joblib

app = FastAPI()

maison_model = joblib.load("regression.joblib")
tumor_model, tumor_scaler = joblib.load("tumor.joblib")

class HouseFeatures(BaseModel):
    taille: float
    nb_chambres: int
    jardin: int

class TumorFeatures(BaseModel):
    size: float
    p53_concentration: float

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API de prédiction"}

@app.post("/predict")
def predict_price(features: List[HouseFeatures]):
    data = [[f.taille, f.nb_chambres, f.jardin] for f in features]
    predictions = maison_model.predict(data)
    results = [
        {
            **f.model_dump(),
            "prediction": predictions[i]
        }
        for i, f in enumerate(features)
    ]
    return results

@app.post("/tumor")
def predict_tumor(features: List[TumorFeatures]):
    data = [[f.size, f.p53_concentration] for f in features]
    scaled_data = tumor_scaler.transform(data)
    predictions = tumor_model.predict(scaled_data)
    results = [
        {
            **f.model_dump(),
            "is_cancerous": int(predictions[i])
        }
        for i, f in enumerate(features)
    ]
    return results
