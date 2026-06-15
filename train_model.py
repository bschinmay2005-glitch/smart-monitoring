import cv2
import os
import sys
import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) < 2:
    print("College ID missing!")
    exit()

college_id = sys.argv[1]

DATASET_PATH = os.path.join(BASE_DIR, "college_data", college_id)
MODEL_FILE = os.path.join(DATASET_PATH, "trainer.yml")
LABEL_FILE = os.path.join(DATASET_PATH, "labels.npy")
print("DATASET_PATH RECEIVED:", DATASET_PATH)
print("DATASET EXISTS:", os.path.exists(DATASET_PATH))
print("DATASET CONTENTS:", os.listdir(DATASET_PATH) if os.path.exists(DATASET_PATH) else "NO FOLDER")
recognizer = cv2.face.LBPHFaceRecognizer_create()
faces = []
ids = []
label_map = {}
if not os.path.exists(DATASET_PATH):
    print("Dataset folder not found!")
    exit()
if os.path.exists(MODEL_FILE):
    os.remove(MODEL_FILE)
if os.path.exists(LABEL_FILE):
    os.remove(LABEL_FILE)
current_id = 0
for root, dirs, files in os.walk(DATASET_PATH):
    image_files = [
        f for f in files
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if len(image_files) == 0:
        continue
    folder_name = os.path.basename(root)
    label_map[current_id] = folder_name
    for image_name in image_files:
        img_path = os.path.join(root, image_name)
        try:
            img = Image.open(img_path).convert("L")
            img_numpy = np.array(img, "uint8")
            faces.append(img_numpy)
            ids.append(current_id)
        except:
            continue
    current_id += 1
if len(faces) == 0:
    print("No training data found!")
    exit()
print("Training model...")
print("Dataset path:", DATASET_PATH)
recognizer.train(faces, np.array(ids))
recognizer.write(MODEL_FILE)
np.save(LABEL_FILE, label_map)
print("Training complete.")
print("Model saved at:", MODEL_FILE)
print("Labels saved at:", LABEL_FILE)
print("Current labels:", label_map)