from fastapi import FastAPI, HTTPException, File, UploadFile, Query
from pydantic import BaseModel
import joblib
import numpy as np
from ultralytics import YOLO
import os
from pathlib import Path
import shutil
from inference_sdk import InferenceHTTPClient
from PIL import Image, ImageDraw
import torch
import torchvision.transforms as transforms
import torchvision.models as models
from collections import defaultdict
import io
from fastapi.responses import JSONResponse, StreamingResponse
from deep_sort_realtime.deepsort_tracker import DeepSort
import matplotlib.pyplot as plt
from aymen.utils import Detector, Tracker
import time
import cv2
from fastapi.middleware.cors import CORSMiddleware
import pickle
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import load_img, img_to_array
from datetime import datetime
import uuid
from fastapi.staticfiles import StaticFiles
from io import BytesIO
import requests

# =============== CONFIGURATION ===============
API_KEY = "RwIjReuDRPVKGFP6bKab"
MODEL_ID = "olive-axotr/3"
CLASS_NAMES = ["kalamata", "manzanilla", "picholine"]
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MODEL_PATH = os.path.join('.', './aymen/modeldet.pt')
VIDEO_UPLOAD_FOLDER = 'uploaded_videos'
FPS_COO = (10, 30)
FPS_THIK = 4
EPS = 2
TEXT_OFFSET = 4
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SIZE = 1
CONF_FS = 0.4
THIKNESS = 2
RED = (0, 0, 255)
WHITE = (255, 255, 255)
ORANGE = (0, 165, 255)
MTR = (72, 209, 204)
MA = (102, 205, 170)
FILL = -1
TEXT = 'olive 999'
TEXT2 = '0.99'
(TEXT_WIDTH, TEXT_HEIGHT), _ = cv2.getTextSize(TEXT, FONT, FONT_SIZE, THIKNESS)
(TEXT_WIDTH2, TEXT_HEIGHT2), _ = cv2.getTextSize(TEXT2, FONT, FONT_SIZE, THIKNESS)
BOX_THIKNESS = 3
CIRCLE_R = 10
Qt_COO = (10, FPS_COO[1] + TEXT_HEIGHT + 2 * TEXT_OFFSET)

# Define custom Cast layer for water accumulation model
class Cast(tf.keras.layers.Layer):
    def __init__(self, target_dtype='float16', **kwargs):
        super(Cast, self).__init__(**kwargs)
        self.target_dtype = target_dtype

    def call(self, inputs):
        return tf.cast(inputs, self.target_dtype)

    def get_config(self):
        config = super().get_config()
        config.update({'target_dtype': self.target_dtype})
        return config

# Register custom object
tf.keras.utils.get_custom_objects().update({'Cast': Cast})

# Initialize FastAPI app
app = FastAPI(title="Olive Oil Classifier and Quality Detection API", version="1.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8081",
        "http://localhost:8081",
        "http://127.0.0.1:8001",
        "http://localhost:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load models
svm_model = joblib.load('./saidane/olive_oil_svm_classifier.pkl')
scaler = joblib.load('./saidane/scaler.pkl')
le = joblib.load('./saidane/label_encoder.pkl')
model = YOLO("BestModelv8.pt")
svm_quality_model = pickle.load(open('./asma/olive_oil_svm_classifier.pkl', 'rb'))
quality_scaler = pickle.load(open('./asma/scaler.pkl', 'rb'))
quality_labelencoder = pickle.load(open('./asma/label_encoder.pkl', 'rb'))
soil_model = joblib.load(r"C:\Users\USER\Desktop\ProjetIA\ApiModels\abbssi\npksoil.pkl")
wildfire_model = joblib.load(r"C:\Users\USER\Desktop\ProjetIA\ApiModels\abbssi\fire.pkl")
insect_model = YOLO("./sahar/olive_insects_detector_model.pt")
water_accumulation_model = tf.keras.models.load_model(
   r"C:\Users\USER\Desktop\ProjetIA\ApiModels\abbssi\wateraccumulation.h5",
    custom_objects={'Cast': Cast},
    compile=False
)
flooding_model = load_model(r"C:\Users\USER\Desktop\ProjetIA\ApiModels\abbssi\flooding.h5")

# Set up upload folders
UPLOAD_FOLDER = 'test_images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VIDEO_UPLOAD_FOLDER, exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load detection model client
client = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)

# Load classification model
classifier = models.resnet50(weights=None)
classifier.fc = torch.nn.Linear(classifier.fc.in_features, len(CLASS_NAMES))
state_dict = torch.load("./saidane/resnet50_zaitun_model.pth", map_location=DEVICE)
classifier.load_state_dict(state_dict, strict=False)
classifier = classifier.to(DEVICE)
classifier.eval()

# Preprocessing for classifier
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Input data models
class OliveOilFeatures(BaseModel):
    palmitic: float
    palmitoleic: float
    stearic: float
    oleic: float
    linoleic: float
    linolenic: float
    arachidic: float
    eicosenoic: float

class QualityFeatures(BaseModel):
    FAEES: float
    K232: float
    K270: float
    Acidity: float
    Peroxide_Index: float

class SoilHealthFeatures(BaseModel):
    pH_Level: float
    Organic_Matter: float
    Nitrogen_Content: float
    Phosphorus_Content: float
    Potassium_Content: float

# Existing endpoints
@app.post("/predict")
async def predict(features: OliveOilFeatures):
    try:
        input_data = np.array([[
            features.palmitic, features.palmitoleic, features.stearic,
            features.oleic, features.linoleic, features.linolenic,
            features.arachidic, features.eicosenoic
        ]])
        scaled_input = scaler.transform(input_data)
        prediction = svm_model.predict(scaled_input)
        predicted_area = le.inverse_transform(prediction)[0]
        return {"predicted_area": predicted_area}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during prediction: {str(e)}")

@app.post("/detect")
async def detect_olive_quality(file: UploadFile = File(...)):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No image provided")
        filename = file.filename
        image_path = Path(UPLOAD_FOLDER) / filename
        with image_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        results = model(str(image_path))
        detections = results[0].boxes.cls.tolist() if results[0].boxes else []
        names = results[0].names
        class_counts = {}
        for c in detections:
            label = names[int(c)]
            class_counts[label] = class_counts.get(label, 0) + 1
        os.remove(image_path)
        return {"status": "success", "detections": class_counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during detection: {str(e)}")

@app.post("/classify")
async def classify(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    temp_path = "temp_uploaded_image.jpg"
    image.save(temp_path)
    try:
        detection_result = client.infer(temp_path, model_id=MODEL_ID)
    except Exception as e:
        os.remove(temp_path)
        return JSONResponse(content={"error": f"Erreur détection: {str(e)}"}, status_code=500)
    
    confidence_scores = defaultdict(list)
    for i, pred in enumerate(detection_result.get("predictions", [])):
        x, y, w, h = pred["x"], pred["y"], pred["width"], pred["height"]
        left = int(x - w / 2)
        top = int(y - h / 2)
        right = int(x + w / 2)
        bottom = int(y + h / 2)
        cropped = image.crop((left, top, right, bottom))
        input_tensor = transform(cropped).unsqueeze(0).to(DEVICE)
        try:
            with torch.no_grad():
                output = classifier(input_tensor)
                _, pred_class = torch.max(output, 1)
                label = CLASS_NAMES[pred_class.item()]
                prob = torch.nn.functional.softmax(output, dim=1)[0][pred_class.item()]
        except Exception as e:
            print(f"Erreur classification pour olive {i+1}: {e}")
            continue
        confidence_scores[label].append(prob.item())

    os.remove(temp_path)

    if confidence_scores:
        average_confidence = {label: sum(scores) / len(scores) for label, scores in confidence_scores.items()}
        predicted_class = max(average_confidence, key=average_confidence.get)
        return predicted_class
    else:
        return "Aucune olive détectée"

@app.post("/quantify")
async def quantify_olives(file: UploadFile = File(...)):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No video provided")
        if not file.filename.lower().endswith(('.mp4', '.avi', '.mov')):
            raise HTTPException(status_code=400, detail="Unsupported video format")

        filename = file.filename
        video_path = Path(VIDEO_UPLOAD_FOLDER) / filename
        with video_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        edgeOliveQuantity = []
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            os.remove(video_path)
            raise HTTPException(status_code=500, detail="Unable to open video file")

        MAX_AGE = int(cap.get(cv2.CAP_PROP_FPS)) * 2
        obj_detector = Detector(MODEL_PATH, confidence=0.6)
        tracker = Tracker(max_age=MAX_AGE)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            detections = obj_detector.detect(frame)
            tracking_ids, boxes = tracker.track(detections, frame)

            if not tracking_ids:
                continue

            if tracking_ids and (not edgeOliveQuantity):
                edgeOliveQuantity.append(tracking_ids)
                continue

            if tracking_ids.isdisjoint(edgeOliveQuantity[-1]):
                edgeOliveQuantity.append(tracking_ids)
            elif tracking_ids > edgeOliveQuantity[-1]:
                edgeOliveQuantity.pop()
                edgeOliveQuantity.append(tracking_ids)

        massOliveQuantity = 0
        for fruit in edgeOliveQuantity:
            massOliveQuantity += len(fruit) * 4e-3

        cap.release()
        os.remove(video_path)

        return round(massOliveQuantity, 3)
    except Exception as e:
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(status_code=500, detail=f"Error during video processing: {str(e)}")

@app.post("/predict2")
async def predict_quality(features: QualityFeatures):
    try:
        input_data = np.array([[features.FAEES, features.K232, features.K270, features.Acidity, features.Peroxide_Index]])
        scaled_input = quality_scaler.transform(input_data)
        prediction_numeric = svm_quality_model.predict(scaled_input)[0]
        quality_label = quality_labelencoder.inverse_transform([prediction_numeric])[0]
        return {"predicted_quality": quality_label}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during quality prediction: {str(e)}")

@app.post("/predict_soil_health")
async def predict_soil_health(features: SoilHealthFeatures):
    try:
        input_data = np.array([[
            features.pH_Level,
            features.Organic_Matter,
            features.Nitrogen_Content,
            features.Phosphorus_Content,
            features.Potassium_Content
        ]])
        prediction = soil_model.predict(input_data)[0]
        predicted_soil_health = "healthy" if prediction == 0 else "unhealthy"
        return {"predicted_soil_health": predicted_soil_health}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during soil health prediction: {str(e)}")

@app.post("/detect_wildfire")
async def detect_wildfire(file: UploadFile = File(...)):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No image provided")
        
        filename = file.filename
        image_path = Path(UPLOAD_FOLDER) / filename
        with image_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        img = cv2.imread(str(image_path))
        if img is None:
            os.remove(image_path)
            raise ValueError("Failed to load image")
        
        img = cv2.resize(img, (32, 32))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img / 255.0
        img = img.reshape(1, 32, 32, 3)
        
        prediction = wildfire_model.predict(img)[0]
        result = "wildfire" if prediction == 1 else "no wildfire"
        
        os.remove(image_path)
        return {"status": "success", "result": result}
    except Exception as e:
        if image_path.exists():
            os.remove(image_path)
        raise HTTPException(status_code=500, detail=f"Error during wildfire detection: {str(e)}")

@app.post("/detect_insects")
async def detect_insects(file: UploadFile = File(...)):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No image provided")
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            raise HTTPException(status_code=400, detail="Unsupported image format")

        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        results = insect_model(image)
        unique_id = uuid.uuid4().hex
        output_filename = f"annotated_{unique_id}.jpg"
        output_path = os.path.join("static", output_filename)
        results[0].save(filename=output_path)

        insect_dict = {
            "Apis_mellifera": "Beneficial",
            "Bactrocera_oleae": "Harmful",
            "Coccinella_septempunctata": "Beneficial",
            "Saissetia_oleae": "Harmful",
            "Crematogaster_scutellaris": "Beneficial",
            "Calocoris_trivialis": "Harmful",
        }
        insectes_detectes = []
        for box in results[0].boxes.data:
            cls_id = int(box[-1])
            cls_name = insect_model.names[cls_id]
            statut = insect_dict.get(cls_name, "unknown")
            insectes_detectes.append({"nom": cls_name, "statut": statut})
            
        try:
            # Envoi des résultats à Node.js
            requests.post("http://localhost:3000/api/save-detection", json={
                "date": datetime.now().isoformat(),
                "image_url": f"/static/{output_filename}",
                "insectes": insectes_detectes
            })
        except Exception as e:
            print("Erreur d'envoi vers Node.js :", e)

        return {"image_url": f"/static/{output_filename}", "insectes": insectes_detectes}
    except Exception as e:
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=f"Error during insect detection: {str(e)}")

# New endpoints for water accumulation and flooding detection
@app.post("/predict_water_accumulation")
async def predict_water_accumulation(file: UploadFile = File(...)):
    try:
        img_bytes = await file.read()
        img = load_img(BytesIO(img_bytes), target_size=(224, 224))
        img_array = img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        prediction = water_accumulation_model.predict(img_array)
        pred_mask = prediction[0, :, :, 0]
        colored_mask = plt.cm.hot(pred_mask)
        colored_mask = (colored_mask[:, :, :3] * 255).astype(np.uint8)
        _, img_encoded = cv2.imencode('.PNG', colored_mask)
        return StreamingResponse(BytesIO(img_encoded.tobytes()), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during water accumulation prediction: {str(e)}")

@app.post("/predict_flooding")
async def predict_flooding(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        image = image.resize((224, 224))
        image = img_to_array(image)
        image = np.expand_dims(image, axis=0)
        image = image / 255.0
        prediction = flooding_model.predict(image)[0][0]
        label = "Flooded" if prediction > 0.5 else "Not Flooded"
        return JSONResponse(content={"prediction": label})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)