import sys
import cv2
import pandas as pd
import numpy as np
import os
from datetime import datetime
from PIL import ImageFont, ImageDraw, Image
import subprocess
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
teacher_username = sys.argv[1]
department = sys.argv[2]
semester = sys.argv[3]
section = sys.argv[4]
subject = sys.argv[5]
college_id = sys.argv[6]
MODEL_FILE = os.path.join(BASE_DIR, "college_data", college_id, "trainer.yml")
LABEL_FILE = os.path.join(BASE_DIR, "college_data", college_id, "labels.npy")
ATTENDANCE_FILE = os.path.join(BASE_DIR, "attendance.csv")
print("Running train_model.py...")
subprocess.call([sys.executable, "train_model.py", college_id])
print("Training completed")
FONT_PATH = "C:/Windows/Fonts/arial.ttf"
font = ImageFont.truetype(FONT_PATH, 22)
if not os.path.exists(MODEL_FILE) or not os.path.exists(LABEL_FILE):
    print("Model not trained. Please run train_model.py first.")
    exit()
recognizer = cv2.face.LBPHFaceRecognizer_create(
    radius=2,
    neighbors=16,
    grid_x=8,
    grid_y=8
)
recognizer.read(MODEL_FILE)
label_map_raw = np.load(LABEL_FILE, allow_pickle=True).item()
label_map = {int(k): v for k, v in label_map_raw.items()}
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
attendance_marked = set()
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    print("Camera not detected!")
    exit()
print("System started... Press ESC to exit.")
while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.2,
        minNeighbors=5,
        minSize=(60, 60)
    )
    for (x, y, w, h) in faces:
        face_roi = gray[y:y+h, x:x+w]
        face_roi = cv2.resize(face_roi, (200, 200))
        id, confidence = recognizer.predict(face_roi)
        if confidence < 60 and id in label_map:
            full_label = label_map[id]
            parts = full_label.split("_")
            student_id = parts[-1]
            name = " ".join(parts[:-1])
           
            CLASS_FOLDER = os.path.join(
                BASE_DIR,
                "college_data",
                college_id,
                department,
                semester,
                section
            )
            student_file = os.path.join(
                CLASS_FOLDER,
                "student_details.csv"
            )
            if not os.path.exists(student_file):
                continue
            class_students = pd.read_csv(student_file).fillna("")
            class_students["ID"] = class_students["ID"].astype(str).str.replace(".0", "", regex=False).str.strip()
            if str(student_id).strip() not in class_students["ID"].tolist():
                print(f"{name} ({student_id}) is not in this class. Ignored.")
                continue
            color = (0,255,0)
            if student_id not in attendance_marked:
                now = datetime.now()
                date = now.strftime("%Y-%m-%d")
                time = now.strftime("%H:%M:%S")
                if not os.path.exists(ATTENDANCE_FILE):
                    pd.DataFrame(
                        columns=[
                            "Teacher",
                            "Name",
                            "ID",
                            "Department",
                            "Semester",
                            "Section",
                            "Subject",
                            "Date",
                            "Time",
                            "Status"
                        ]
                    ).to_csv(ATTENDANCE_FILE,index=False)
                df = pd.read_csv(ATTENDANCE_FILE)
                required_columns = [
                    "Teacher",
                    "Name",
                    "ID",
                    "Department",
                    "Semester",
                    "Section",
                    "Subject",
                    "Date",
                    "Time",
                    "Status"
                ]
                for col in required_columns:
                    if col not in df.columns:
                        df[col] = "-"
                already_marked = df[
                    (df["Teacher"].astype(str) == str(teacher_username)) &
                    (df["ID"].astype(str) == str(student_id)) &
                    (df["Department"].astype(str).str.upper() == str(department).upper()) &
                    (df["Semester"].astype(str) == str(semester)) &
                    (df["Section"].astype(str).str.upper() == str(section).upper()) &
                    (df["Subject"].astype(str) == str(subject)) &
                    (df["Date"].astype(str) == str(date))
                ]
                if already_marked.empty:
                    new_row = pd.DataFrame(
                        [[
                            teacher_username,
                            name,
                            student_id,
                            department,
                            semester,
                            section,
                            subject,
                            date,
                            time,
                            "Present"
                        ]],
                        columns=[
                            "Teacher",
                            "Name",
                            "ID",
                            "Department",
                            "Semester",
                            "Section",
                            "Subject",
                            "Date",
                            "Time",
                            "Status"
                        ]
                    )
                    df = pd.concat([df, new_row], ignore_index=True)
                    df.to_csv(ATTENDANCE_FILE, index=False)
                    attendance_marked.add(student_id)
                    print(f"{name} marked present.")
                else:
                    print(f"{name} already marked today.")
        else:
            name = "Unknown"
            student_id = ""
            color = (0,0,255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
        label = name if name == "Unknown" else f"{name} | {student_id}"
        img_pil = Image.fromarray(frame)
        draw = ImageDraw.Draw(img_pil)
        draw.text(
            (x, y-30),
            label,
            font=font,
            fill=(0,255,0)
        )
        frame = np.array(img_pil)
    cv2.imshow("Face Attendance System", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break
cap.release()
cv2.destroyAllWindows()