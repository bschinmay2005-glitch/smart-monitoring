import cv2
import os
import sys
import pandas as pd
from tkinter import Tk, messagebox
import numpy as np
import subprocess
import shutil
try:
    NAME = sys.argv[1]
    ID = sys.argv[2]
    PHONE = sys.argv[3]
    P_NAME = sys.argv[4]
    P_PHONE = sys.argv[5]
    GENDER = sys.argv[6]
    DEPARTMENT = sys.argv[7]
    SEMESTER = sys.argv[8]
    SECTION = sys.argv[9]
    base_path = sys.argv[10]
except IndexError:
    print("Error: Arguments missing from app.py")
    sys.exit(1)
root = Tk()
root.withdraw()
name = NAME
student_id = ID
phone = PHONE
parent_name = P_NAME
parent_phone = P_PHONE
gender = GENDER
department = DEPARTMENT
semester = SEMESTER
section = SECTION
print(f"Website data received: {name}, {student_id}, {phone}")
safe_name = name.replace(" ", "_")
os.makedirs(base_path, exist_ok=True)
dataset_base_path = os.path.join(base_path, "dataset")
os.makedirs(dataset_base_path, exist_ok=True)
dataset_path = os.path.join(
    dataset_base_path,
    safe_name + "_" + student_id
)
os.makedirs(dataset_path, exist_ok=True)
print("FINAL DATASET PATH:", dataset_path)
face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
college_root = os.path.dirname(
    os.path.dirname(
        os.path.dirname(base_path)
    )
)
print("BASE PATH:", base_path)
print("COLLEGE ROOT:", college_root)
print("REGISTERING STUDENT ID:", student_id)
print("FILES INSIDE COLLEGE ROOT:")

for root_dir, dirs, files in os.walk(college_root):
    print(root_dir, files)

student_id_exists = False

for root_dir, dirs, files in os.walk(college_root):
    if "student_details.csv" in files:
        student_file = os.path.join(root_dir, "student_details.csv")
        existing_df = pd.read_csv(student_file).fillna("")
        existing_df["ID"] = existing_df["ID"].astype(str).str.replace(".0", "", regex=False).str.strip()

        if str(student_id).strip() in existing_df["ID"].tolist():
            student_id_exists = True
            break

if student_id_exists:
    messagebox.showwarning(
        "Already Registered",
        "This Student ID is already registered in this college."
    )

    if os.path.exists(dataset_path):
        shutil.rmtree(dataset_path)

    sys.exit()
print("Training model before duplicate face check...")
college_id = os.path.basename(college_root)

subprocess.call([
    sys.executable,
    "train_model.py",
    college_id
])
print("Training completed")
print("MODEL EXISTS:", os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "college_data", "trainer.yml")))
print("LABEL EXISTS:", os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "college_data", "labels.npy")))

MODEL_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "college_data",
    "trainer.yml"
)

LABEL_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "college_data",
    "labels.npy"
)

recognizer = None
label_map = {}

if os.path.exists(MODEL_FILE) and os.path.exists(LABEL_FILE):
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_FILE)
    label_map = np.load(LABEL_FILE, allow_pickle=True).item()
    label_map = {int(k): v for k, v in label_map.items()}
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Camera not detected")
    sys.exit()
print("Opening camera...")
count = 0
capture_started = False
confirmation_shown = False
face_detected = False
while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(60,60)
    )
    face_detected = False
    for (x,y,w,h) in faces:

        face_detected = True

        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face,(200,200))
        if recognizer is not None:
            predicted_id, confidence = recognizer.predict(face)
            print("FACE CHECK CONFIDENCE:", confidence)
            print("PREDICTED ID:", predicted_id)
            print("LABEL MAP:", label_map)

            if confidence < 95 and predicted_id in label_map:
                existing_student = label_map[predicted_id]

                messagebox.showwarning(
                    "Already Registered",
                    f"This face is already registered as {existing_student}.\nPlease show a new face."
                )

                if os.path.exists(dataset_path):
                    shutil.rmtree(dataset_path)

                cap.release()
                cv2.destroyAllWindows()
                sys.exit()

        cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
        if capture_started:
                face = gray[y:y+h, x:x+w]
                face = cv2.resize(face,(200,200))
                count += 1
                file_name = os.path.join(dataset_path, f"{count}.jpg")
                cv2.imwrite(file_name, face)
                print("Saved:", file_name)
                cv2.putText(
                    frame,
                    f"Capturing {name} ({count}/50)",
                    (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0,255,0),
                    2
                )
    cv2.imshow("Camera", frame)

    if face_detected and not confirmation_shown:

        confirmation_shown = True

        answer = messagebox.askyesno(
            "Face Detected",
            "Do you want to capture this face?"
        )

        if answer:
            capture_started = True
            print("User approved capture.")
        else:
            print("User rejected capture.")
            break
    if count >= 50:
        break
    if cv2.waitKey(1) & 0xFF == 27:
        break
cap.release()
cv2.destroyAllWindows()
print("TOTAL IMAGES CAPTURED:", count)
print("SAVING TO:", dataset_path)
if count > 0:
    file_path = os.path.join(base_path, "student_details.csv")
    new_student_data = {
        "Name": [name],
        "ID": [student_id],
        "Phone": [phone],
        "Parent": [parent_name],
        "P_Phone": [parent_phone],
        "Gender": [gender],
        "Department": [department],
        "Semester": [semester],
        "Section": [section]
    }
    df_new = pd.DataFrame(new_student_data)
    if not os.path.exists(file_path):
        # Create file with headers if it doesn't exist
        df_new.to_csv(file_path, index=False)
    else:
        # Append to existing file and remove duplicates
        df_old = pd.read_csv(file_path)
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
        df_combined.drop_duplicates(subset=["ID"], keep="last", inplace=True)
        df_combined.to_csv(file_path, index=False)
    print(f"Registration complete. Details for {name} saved to {file_path}")
else:
    print("Registration cancelled or incomplete. No data saved.")
print("Finished capturing faces.")