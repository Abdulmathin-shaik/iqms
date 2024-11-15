import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import sqlite3
from tkinter import filedialog
from ultralytics import YOLO
import os
from datetime import datetime

class ScrewDetectionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Screw Detection System")
        self.root.geometry("800x600")

        # Initialize variables
        self.chamber_number = tk.StringVar()
        self.image_path = None
        self.captured_image = None
        
        # Create database and table
        self.create_database()
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Initialize loading label
        self.loading_label = ttk.Label(self.main_frame, text="Loading YOLOv8n model...")
        self.loading_label.grid(row=0, column=0, columnspan=2)
        self.root.update()

        try:
            # Initialize YOLO model (will download if not present)
            self.model = YOLO('yolov8n.pt')
            self.loading_label.destroy()
            self.setup_initial_screen()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load model: {str(e)}")
            self.loading_label.config(text="Error loading model")

    def create_database(self):
        conn = sqlite3.connect('screw_detection.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                chamber_number TEXT PRIMARY KEY,
                missing_screw_count INTEGER,
                good_screw_count INTEGER,
                timestamp DATETIME
            )
        ''')
        conn.commit()
        conn.close()

    def setup_initial_screen(self):
        # Chamber number entry
        ttk.Label(self.main_frame, text="Enter Chamber Number:").grid(row=0, column=0, pady=10)
        chamber_entry = ttk.Entry(self.main_frame, textvariable=self.chamber_number)
        chamber_entry.grid(row=0, column=1, pady=10)
        
        ttk.Button(self.main_frame, text="Submit", command=self.show_image_options).grid(row=1, column=0, columnspan=2, pady=10)

    def show_image_options(self):
        if not self.chamber_number.get():
            messagebox.showerror("Error", "Please enter a chamber number")
            return
            
        # Clear previous widgets
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        # Show image acquisition options
        ttk.Button(self.main_frame, text="Upload Image", command=self.upload_image).grid(row=0, column=0, pady=10, padx=5)
        ttk.Button(self.main_frame, text="Take Image", command=self.take_image).grid(row=0, column=1, pady=10, padx=5)

    def upload_image(self):
        self.image_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff")]
        )
        if self.image_path:
            self.show_inference_button()

    def take_image(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error", "Cannot access camera")
            return
            
        ret, frame = cap.read()
        if ret:
            self.captured_image = frame
            # Save captured image temporarily
            cv2.imwrite("temp_capture.jpg", frame)
            self.image_path = "temp_capture.jpg"
            self.show_inference_button()
        
        cap.release()

    def show_inference_button(self):
        # Display selected/captured image
        img = Image.open(self.image_path)
        img = img.resize((400, 300))
        photo = ImageTk.PhotoImage(img)
        
        # Clear previous widgets
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        # Show image
        image_label = ttk.Label(self.main_frame, image=photo)
        image_label.image = photo
        image_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Add inference button
        ttk.Button(self.main_frame, text="Run Inference", command=self.run_inference).grid(row=1, column=0, columnspan=2, pady=10)

    def run_inference(self):
        try:
            # Show loading message
            loading_label = ttk.Label(self.main_frame, text="Running inference...")
            loading_label.grid(row=2, column=0, columnspan=2)
            self.root.update()

            # Run YOLO inference
            results = self.model(self.image_path)
            
            # Process results based on class count
            class_counts = {0: 0, 1: 0}  # Initialize counters for both classes
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    if cls in class_counts:
                        class_counts[cls] += 1

            missing_count = class_counts[0]  # Class 0 count
            good_count = class_counts[1]     # Class 1 count
            
            # Save results
            self.save_results(missing_count, good_count)
            
            # Show results
            results[0].save(f"results/{self.chamber_number.get()}.jpg")
            
            # Remove loading label
            loading_label.destroy()
            
            # Display results
            self.show_results(missing_count, good_count)
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during inference: {str(e)}")

    def save_results(self, missing_count, good_count):
        # Save to database
        conn = sqlite3.connect('screw_detection.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO detections 
            (chamber_number, missing_screw_count, good_screw_count, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (self.chamber_number.get(), missing_count, good_count, datetime.now()))
        conn.commit()
        conn.close()
        
        # Create results directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
        
        # Save original image with chamber number as filename
        if self.image_path:
            img = Image.open(self.image_path)
            img.save(f"results/{self.chamber_number.get()}_original.jpg")

    def show_results(self, missing_count, good_count):
        # Clear previous widgets
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        # Display results
        ttk.Label(self.main_frame, text=f"Chamber Number: {self.chamber_number.get()}").grid(row=0, column=0, columnspan=2, pady=5)
        ttk.Label(self.main_frame, text=f"Missing Screws: {missing_count}").grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Label(self.main_frame, text=f"Good Screws: {good_count}").grid(row=2, column=0, columnspan=2, pady=5)
        
        # Show annotated image
        result_img = Image.open(f"results/{self.chamber_number.get()}.jpg")
        result_img = result_img.resize((400, 300))
        photo = ImageTk.PhotoImage(result_img)
        
        result_label = ttk.Label(self.main_frame, image=photo)
        result_label.image = photo
        result_label.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Add new session button
        ttk.Button(self.main_frame, text="New Session", command=self.setup_initial_screen).grid(row=4, column=0, columnspan=2, pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = ScrewDetectionGUI(root)
    root.mainloop()