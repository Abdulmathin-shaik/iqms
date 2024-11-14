# main.py
from fastapi import FastAPI, File, UploadFile, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
import os
import base64
from pathlib import Path
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from database import Detection, get_db

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
async def upload_file(
    file: UploadFile, 
    chamber_number: str = Form(...),
    db: Session = Depends(get_db)
):
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
    
    # Save to database
    db_detection = Detection(
        chamber_number=chamber_number,
        image_path=str(file_path),
        result_image_path=str(result_path),
        detections=detections
    )
    db.add(db_detection)
    db.commit()
    db.refresh(db_detection)
    
    return {
        "id": db_detection.id,
        "chamber_number": chamber_number,
        "result_image": str(result_path),
        "detections": detections,
        "timestamp": db_detection.timestamp
    }

@app.post("/capture")
async def capture_image(
    image_data: str = Form(...), 
    chamber_number: str = Form(...),
    db: Session = Depends(get_db)
):
    # Convert base64 image to file
    image_data = image_data.split(",")[1]
    image_bytes = io.BytesIO(base64.b64decode(image_data))
    image = Image.open(image_bytes)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capture_{chamber_number}_{timestamp}.jpg"
    
    # Save captured image
    file_path = UPLOAD_DIR / filename
    image.save(file_path)
    
    # Run inference
    results = model(str(file_path))
    
    # Save result image
    result_path = RESULT_DIR / f"result_{filename}"
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
    
    # Save to database
    db_detection = Detection(
        chamber_number=chamber_number,
        image_path=str(file_path),
        result_image_path=str(result_path),
        detections=detections
    )
    db.add(db_detection)
    db.commit()
    db.refresh(db_detection)
    
    return {
        "id": db_detection.id,
        "chamber_number": chamber_number,
        "result_image": str(result_path),
        "detections": detections,
        "timestamp": db_detection.timestamp
    }

@app.get("/detections")
async def get_detections(
    chamber_number: str = None,
    db: Session = Depends(get_db)
) -> List[Detection]:
    """Get all detections, optionally filtered by chamber number"""
    query = db.query(Detection)
    if chamber_number:
        query = query.filter(Detection.chamber_number == chamber_number)
    return query.all()

@app.get("/detection/{detection_id}")
async def get_detection(
    detection_id: int,
    db: Session = Depends(get_db)
) -> Detection:
    """Get a specific detection by ID"""
    return db.query(Detection).filter(Detection.id == detection_id).first()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)