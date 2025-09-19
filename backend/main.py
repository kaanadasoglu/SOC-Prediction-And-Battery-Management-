from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
import joblib
import numpy as np
import os
from pymongo import MongoClient
from bson.binary import Binary
from clean_data import load_clean_battery
import io
import paho.mqtt.client as mqtt
import json
import tensorflow as tf  

app = FastAPI(title="Battery SOC Prediction")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongo:27017/batterydb")
client = MongoClient(MONGO_URI)
db = client.batterydb
battery_collection = db.batteries  

linearRegression = joblib.load("models/LinearRegression.joblib")
decisionTree = joblib.load("models/DecisionTree.joblib")
randomForest = joblib.load("models/RandomForest.joblib")
xgBoost = joblib.load("models/XGBoost.joblib")

lstm_model = tf.keras.models.load_model("models/LSTM.keras")


features = [
    "Re", "Rct", "Sense_current_max", "Temperature_measured_min",
    "time_min", "Current_load_mean", "Rectified_Impedance_std",
    "Voltage_measured_mean", "Current_measured_mean", "time_std"
]


MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "battery/soc"

mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()


def get_test_set(battery_name: str):
    bat = battery_collection.find_one({"name": battery_name})
    if not bat or "mat_file" not in bat:
        return None
    mat_bytes = bat["mat_file"]
    return load_clean_battery(io.BytesIO(mat_bytes))

def make_sequences(data, window_size=10):
    sequences = []
    for i in range(len(data) - window_size):
        sequences.append(data[i:i+window_size])
    return np.array(sequences)


@app.get("/predict_all/{battery_name}")
def predict_all(
    battery_name: str, 
    model_name: str = "LinearRegression",
    future_steps: int = Query(5, ge=1, le=50, description="İleri tahmin adımı")
):
    df = get_test_set(battery_name)
    if df is None:
        return {battery_name: []}

    models = {
        "LinearRegression": linearRegression,
        "DecisionTree": decisionTree,
        "RandomForest": randomForest,
        "XGBoost": xgBoost,
        "LSTM": lstm_model
    }
    if model_name not in models:
        return {"error": f"Geçersiz model seçildi: {model_name}"}

    selected_model = models[model_name]
    X = df[features].values
    window_size = 10


    if model_name == "LSTM":
        sequences = make_sequences(X, window_size)
        predicted = selected_model.predict(sequences).flatten().tolist()

        last_seq = X[-window_size:].reshape(1, window_size, len(features))
        future_preds = []
        current_seq = last_seq.copy()

        for _ in range(future_steps):
            next_pred = selected_model.predict(current_seq)[0][0]
            future_preds.append(float(next_pred))

            # pencereyi kaydır ve son tahmini güncelle
            new_row = np.zeros((1, 1, len(features)))
            new_row[0, 0, :-1] = current_seq[0, -1, :-1]
            new_row[0, 0, -1] = next_pred
            current_seq = np.append(current_seq[:, 1:, :], new_row, axis=1)

        soc_preds = {"predicted": predicted, "forecast": future_preds}


    else:
        predicted = []
        future_preds = []

     
        for i in range(len(X)):
            x_row = X[i].reshape(1, -1)
            soc_val = float(selected_model.predict(x_row)[0])
            predicted.append(soc_val)

 
        last_window = X[-window_size:].copy() if len(X) >= window_size else X.copy()
        for _ in range(future_steps):
            x_input = last_window[-1].reshape(1, -1)
            next_val = float(selected_model.predict(x_input)[0])
            future_preds.append(next_val)

     
            new_row = last_window[-1].copy()
            new_row[-1] = next_val  
            if len(last_window) >= window_size:
                last_window = np.vstack([last_window[1:], new_row])
            else:
                last_window = np.vstack([last_window, new_row])

        soc_preds = {"predicted": predicted, "forecast": future_preds}


    mqtt_client.publish(MQTT_TOPIC, json.dumps({
        "battery": battery_name,
        "event": "predicted",
        "model": model_name,
        "soc": soc_preds
    }))

    return soc_preds


@app.post("/upload_battery/")
async def upload_battery(file: UploadFile = File(...)):
    content = await file.read()
    battery_name = os.path.splitext(file.filename)[0]

    try:
        new_battery_df = load_clean_battery(io.BytesIO(content))
    except Exception as e:
        return {"error": f"Dosya işlenirken hata oluştu: {e}"}

    battery_collection.update_one(
        {"name": battery_name},
        {"$set": {"mat_file": Binary(content)}},
        upsert=True
    )

    mqtt_client.publish(MQTT_TOPIC, json.dumps({
        "battery": battery_name,
        "event": "uploaded"
    }))

    return {"message": f"{battery_name} MongoDB'ye kaydedildi ve test set hazır."}


@app.get("/list_batteries/")
def list_batteries():
    batteries = [b["name"] for b in battery_collection.find()]
    return {"batteries": batteries}
