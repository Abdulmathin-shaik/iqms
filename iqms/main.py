# main.py
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
import os
import base64
from pathlib import Path

app = FastAPI()

# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create directories if they don't exist
UPLOAD_DIR = Path("uploads")
RESULT_DIR = Path("results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# Load the YOLOv8n model
model = YOLO('yolov8n.pt')

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html") as f:
        return f.read()

@app.post("/upload")
async def upload_file(file: UploadFile, chamber_number: str = Form(...)):
    # Save the uploaded file
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Run inference
    results = model(str(file_path))
    
    # Save the result image with bounding boxes
    result_path = RESULT_DIR / f"result_{file.filename}"
    result_img = results[0].plot()
    cv2.imwrite(str(result_path), result_img)
    
    # Get detection results
    detections = []
    for r in results:
        for box in r.boxes:
            detection = {
                "class": model.names[int(box.cls)],
                "confidence": float(box.conf),
                "bbox": box.xyxy[0].tolist()
            }
            detections.append(detection)
    
    return {
        "chamber_number": chamber_number,
        "result_image": str(result_path),
        "detections": detections
    }

@app.post("/capture")
async def capture_image(image_data: str = Form(...), chamber_number: str = Form(...)):
    # Convert base64 image to file
    image_data = image_data.split(",")[1]
    image_bytes = io.BytesIO(base64.b64decode(image_data))
    image = Image.open(image_bytes)
    
    # Save captured image
    file_path = UPLOAD_DIR / f"capture_{chamber_number}.jpg"
    image.save(file_path)
    
    # Run inference
    results = model(str(file_path))
    
    # Save result image
    result_path = RESULT_DIR / f"result_capture_{chamber_number}.jpg"
    result_img = results[0].plot()
    cv2.imwrite(str(result_path), result_img)
    
    # Get detection results
    detections = []
    for r in results:
        for box in r.boxes:
            detection = {
                "class": model.names[int(box.cls)],
                "confidence": float(box.conf),
                "bbox": box.xyxy[0].tolist()
            }
            detections.append(detection)
    
    return {
        "chamber_number": chamber_number,
        "result_image": str(result_path),
        "detections": detections
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)