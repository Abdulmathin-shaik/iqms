import tkinter as tk

from tkinter import filedialog

from PIL import Image, ImageTk

import cv2

import torch

from ultralytics import YOLO

import sqlite3



# Load YOLOv8 model

model = YOLO("yolov8s.yaml")



# Create database connection

conn = sqlite3.connect('results.db')

c = conn.cursor()



# Create table if not exists

c.execute('''CREATE TABLE IF NOT EXISTS results

             (chamber_number text, missing_screws integer, good_screws integer)''')

conn.commit()



def upload_image():

    path = filedialog.askopenfilename(filetypes=[("Image Files", ".jpg.jpeg.png.bmp")])

    if path:

        img = cv2.imread(path)

        cv2.imwrite("temp.jpg", img)

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(img)

        img.thumbnail((400, 400))

        img = ImageTk.PhotoImage(img)

        label.config(image=img)

        label.image = img

        entry.config(state="normal")

        run_button.config(state="normal")



def capture_image():

    cap = cv2.VideoCapture(0)

    ret, frame = cap.read()

    cap.release()

    if ret:

        cv2.imwrite("temp.jpg", frame)

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(img)

        img.thumbnail((400, 400))

        img = ImageTk.PhotoImage(img)

        label.config(image=img)

        label.image = img

        entry.config(state="normal")

        run_button.config(state="normal")



def run_inference():

    chamber_number = entry.get()

    if chamber_number:

        img = cv2.imread("temp.jpg")

        results = model(img)

        missing_screws = 0

        good_screws = 0

        for result in results.xyxy[0]:

            if result[5] == 0:

                missing_screws += 1

            elif result[5] == 1:

                good_screws += 1

        cv2.imwrite(f"{chamber_number}.jpg", img)

        c.execute("INSERT INTO results VALUES (?,?,?)",

                  (chamber_number, missing_screws, good_screws))

        conn.commit()

        result_text.delete(1.0, tk.END)

        result_text.insert(tk.END, f"Missing screws: {missing_screws}\nGood screws: {good_screws}")



root = tk.Tk()

root.title("Screw Classification")



upload_button = tk.Button(root, text="Upload Image", command=upload_image)

upload_button.pack()



capture_button = tk.Button(root, text="Capture Image", command=capture_image)

capture_button.pack()



label = tk.Label(root)

label.pack()



entry_label = tk.Label(root, text="Enter Chamber Number:")

entry_label.pack()

entry = tk.Entry(root)

entry.pack()

entry.config(state="disabled")



run_button = tk.Button(root, text="Run Inference", command=run_inference)

run_button.pack()

run_button.config(state="disabled")



result_text = tk.Text(root)

result_text.pack()



root.mainloop()