# from database import create_table
from flask import Flask, render_template, redirect, request, jsonify, session
from supabase_client import supabase
import subprocess
import pandas as pd
import random
import os
import sys
from datetime import datetime
import json

COLLEGE_DATA_FILE = "colleges.json"
PENDING_COLLEGES_FILE = "pending_colleges.json"
def load_colleges():
    if os.path.exists(COLLEGE_DATA_FILE):
        with open(COLLEGE_DATA_FILE, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}
def load_pending():
    if os.path.exists(PENDING_COLLEGES_FILE):
        with open(PENDING_COLLEGES_FILE, "r") as f:
            try: return json.load(f)
            except: return []
    return []
app = Flask(__name__)
app.secret_key = "bca_project_secure_key"
create_table()
camera_process = None
@app.route("/")
def index():
    return render_template("index.html")
@app.route("/login")
def teacher_login_page():
    return render_template("login.html")
@app.route("/college_admin_login")
def college_admin_login():
    return render_template("college_admin_login.html")
@app.route("/login_action", methods=["POST"])
def login_action():
    username = request.form.get("username")
    password = request.form.get("password")

    result = (
        supabase
        .table("teachers")
        .select("*")
        .eq("username", username)
        .eq("password", password)
        .execute()
    )

    if result.data:
        teacher = result.data[0]

        session["logged_in"] = True
        session["username"] = teacher["username"]
        session["teacher_name"] = teacher["name"]

        return redirect("/admin")

    return "<h1>Invalid Credentials. <a href='/login'>Try Again</a></h1>"
@app.route("/login_auth", methods=["POST"])
def login_auth():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if os.path.exists("registered_teachers.txt"):
        with open("registered_teachers.txt", "r") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    parts = line.split(" | ")
                    stored_user = parts[3].replace("User: ", "").strip()
                    stored_pass = parts[4].replace("Pass: ", "").strip()
                    if username == stored_user and password == stored_pass:
                        teacher_name = parts[1].replace("Name: ", "").strip()
                        teacher_department = parts[2].replace("Department: ", "").strip()
                        assignments_file = "teacher_assignments.csv"

                        if not os.path.exists(assignments_file):
                            return jsonify({
                                "success": False,
                                "message": "You are not assigned to any class yet. Please contact college admin."
                            }), 403

                        assignments = pd.read_csv(assignments_file).fillna("")

                        assigned = assignments[
                            assignments["TeacherUsername"].astype(str).str.strip()
                            ==
                            str(username).strip()
                        ]

                        if assigned.empty:
                            return jsonify({
                                "success": False,
                                "message": "You are not assigned to any class yet. Please contact college admin."
                            }), 403
                        session['logged_in'] = True
                        session['username'] = username
                        session['teacher_name'] = teacher_name
                        session['teacher_department'] = teacher_department
                        return jsonify({"success": True})
                except Exception as e:
                    print(f"Skipping messy line in text file: {e}")
                    continue
    return jsonify({"success": False, "message": "Invalid credentials"}), 401  
@app.route("/college_admin_auth", methods=["POST"])
def college_admin_auth():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    colleges = load_colleges()
    for cid, info in colleges.items():
        if not isinstance(info, dict):
            continue
        if (
            info.get("admin_username") == username and
            info.get("admin_password") == password
        ):
            session['college_admin'] = True
            session['college_id'] = cid
            session['college_name'] = info.get("name")
            return jsonify({"success": True})
    return jsonify({"success": False}), 401
@app.route("/college_admin_dashboard")
def college_admin_dashboard():
    if not session.get("college_admin"):
        return redirect("/college_admin_login")
    return render_template(
        "college_admin_dashboard.html",
        college_name=session.get("college_name")
    )
@app.route("/assign_teacher", methods=["POST"])
def assign_teacher():
    if not session.get("college_admin"):
        return jsonify({
            "success": False,
            "message": "Please login as college admin first"
        }), 401
    data = request.get_json()
    college_id = session.get("college_id")
    teacher_username = data.get("teacher_username", "").strip()
    department = data.get("department", "").strip().upper()
    semester = data.get("semester", "").strip()
    section = data.get("section", "").strip().upper()
    subject = data.get("subject", "").strip()
    start_date = data.get("start_date", "").strip()
    end_date = data.get("end_date", "").strip()
    day = data.get("day", "").strip()
    start_time = data.get("start_time", "").strip()
    end_time = data.get("end_time", "").strip()
    if not teacher_username or not department or not semester or not section or not subject:
        return jsonify({
            "success": False,
            "message": "Please fill teacher, class and subject"
        }), 400
    file_path = "teacher_assignments.csv"
    new_data = pd.DataFrame([{
        "CollegeID": college_id,
        "TeacherUsername": teacher_username,
        "Department": department,
        "Semester": semester,
        "Section": section,
        "Subject": subject,
        "StartDate": start_date,
        "EndDate": end_date,
        "Status": "Active",
        "Day": day,
        "StartTime": start_time,
        "EndTime": end_time
    }])
    if os.path.exists(file_path):
        old_data = pd.read_csv(file_path)
        old_data = old_data.fillna("")
        for col in new_data.columns:
            if col not in old_data.columns:
                old_data[col] = ""
        final_data = pd.concat([old_data, new_data], ignore_index=True)
    else:
        final_data = new_data
    final_data.to_csv(file_path, index=False)
    return jsonify({
        "success": True,
        "message": "Teacher assigned successfully"
    })
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/register_teacher", methods=["POST"])
def register_teacher():
    data = request.get_json()
    name = data.get("name")
    department = data.get("department")
    teacher_id = random.randint(1000, 9999)
    college_id = data.get("c_id")
    college_id = college_id.replace("Pass", "")
    print("Entered College ID:", college_id)
    approved_colleges = load_colleges()
    if college_id not in approved_colleges:
        return jsonify({
            "success": False, 
            "message": "Invalid College ID. Please contact Admin."
        }), 403
    generated_username = f"{name.replace(' ', '_')}_{teacher_id}"
    generated_password = f"{college_id}Pass"
    with open("registered_teachers.txt", "a") as f:
        f.write(f"CollegeID: {college_id} | Name: {name} | Department: {department} | User: {generated_username} | Pass: {generated_password}\n")
    return jsonify({
        "success": True, 
        "username": generated_username, 
        "password": generated_password
    })

@app.route("/admin")
def admin():    
    if not session.get('logged_in'):
        return redirect("/login")
    attendance_file = "attendance.csv"
    total_students = 0
    base_folder = "college_data"
    if os.path.exists(base_folder):
        for department in os.listdir(base_folder):
            dept_path = os.path.join(base_folder, department)
            if not os.path.isdir(dept_path):
                continue
            for semester in os.listdir(dept_path):
                sem_path = os.path.join(dept_path, semester)
                if not os.path.isdir(sem_path):
                    continue
                for section in os.listdir(sem_path):

                    student_file = os.path.join(
                        sem_path,
                        section,
                        "student_details.csv"
                    )
                    if os.path.exists(student_file):
                        df_students = pd.read_csv(student_file)
                        total_students += len(df_students)
    if os.path.exists(attendance_file):
        df = pd.read_csv(attendance_file)
    else:
        df = pd.DataFrame(
        columns=[
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
    if "Status" not in df.columns:
        df["Status"] = "Present"
    else:
        df["Status"] = df["Status"].fillna("Present")
    today_date = datetime.now().strftime("%Y-%m-%d")
    clean_df = df.drop_duplicates(
        subset=["ID", "Department", "Semester", "Section", "Subject", "Date"],
        keep="first"
    )
    clean_df.to_csv(attendance_file, index=False)
    total_records = clean_df.shape[0]
    today_attendance = clean_df[
        (clean_df["Date"] == today_date) &
        (clean_df["Status"] == "Present")
    ]["ID"].nunique()
    return render_template(
    "admin.html",
    total_students=total_students,
    today_attendance=today_attendance,
    total_records=total_records,
    teacher_name=session.get("teacher_name", "Unknown"),
    teacher_department=session.get("teacher_department", "Unknown")
)

@app.route("/records_data")
def records_data():
    teacher_username = str(session.get("username", "")).strip()
    department = request.args.get("department", "").strip().upper()
    semester = request.args.get("semester", "").strip()
    section = request.args.get("section", "").strip().upper()
    subject = request.args.get("subject", "").strip()
    attendance_file = "attendance.csv"
    if not os.path.exists(attendance_file):
        return jsonify([])
    df = pd.read_csv(attendance_file).fillna("-")
    for col in ["Teacher", "Department", "Semester", "Section", "Subject"]:
        if col not in df.columns:
            df[col] = "-"
    df["Teacher"] = df["Teacher"].astype(str).str.strip()
    df["Department"] = df["Department"].astype(str).str.strip().str.upper()
    df["Semester"] = df["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Section"] = df["Section"].astype(str).str.strip().str.upper()
    df["Subject"] = df["Subject"].astype(str).str.strip()
    df = df[
        (df["Teacher"] == teacher_username) &
        (df["Department"] == department) &
        (df["Semester"] == semester) &
        (df["Section"] == section) &
        (df["Subject"] == subject)
    ]
    df = df.drop_duplicates(
        subset=["Teacher", "ID", "Department", "Semester", "Section", "Subject", "Date"],
        keep="first"
    )
    return jsonify(df.to_dict(orient="records"))

@app.route("/start_attendance")
def start_attendance():
    global camera_process
    if camera_process:
        camera_process.terminate()
        camera_process = None
    teacher_username = session.get("username")
    department = request.args.get("department")
    semester = request.args.get("semester")
    section = request.args.get("section")
    subject = request.args.get("subject")
    college_id = session.get("college_id")

    if not college_id:
        assignments_file = "teacher_assignments.csv"
        if os.path.exists(assignments_file):
            assignments = pd.read_csv(assignments_file).fillna("")
            matched = assignments[
                assignments["TeacherUsername"].astype(str).str.strip() == str(teacher_username).strip()
            ]
            if not matched.empty and "CollegeID" in matched.columns:
                college_id = matched.iloc[0]["CollegeID"]

    camera_process = subprocess.Popen(
    [
        sys.executable,
        "attendance.py",
        teacher_username,
        department,
        semester,
        section,
        subject,
        college_id
    ]
    )
    return "", 204

@app.route("/student_login_action", methods=["POST"])
def student_login_action():
    student_id = request.form.get("student_id")
    if not student_id:
        return redirect("/student_portal")
    session["student_id"] = student_id
    return redirect("/student_dashboard")

@app.route("/student_portal")
def student_portal():
    return render_template("student_login.html")
@app.route("/student_dashboard")
def student_dashboard():

    student_id = session.get("student_id")

    if not student_id:
        return redirect("/student_portal")

    base_folder = "college_data"

    if not os.path.exists(base_folder):
        return redirect("/student_portal")

    for college_id in os.listdir(base_folder):

        college_path = os.path.join(base_folder, college_id)

        if not os.path.isdir(college_path):
            continue

        for department in os.listdir(college_path):

            dept_path = os.path.join(college_path, department)

            if not os.path.isdir(dept_path):
                continue

            for semester in os.listdir(dept_path):

                sem_path = os.path.join(dept_path, semester)

                if not os.path.isdir(sem_path):
                    continue

                for section in os.listdir(sem_path):

                    section_path = os.path.join(sem_path, section)

                    if not os.path.isdir(section_path):
                        continue

                    student_file = os.path.join(
                        section_path,
                        "student_details.csv"
                    )

                    if os.path.exists(student_file):

                        df = pd.read_csv(student_file).fillna("-")

                        matched = df[
                            df["ID"].astype(str).str.strip()
                            ==
                            str(student_id).strip()
                        ]

                        if not matched.empty:

                            student = matched.iloc[0].to_dict()

                            student["Department"] = department
                            student["Semester"] = semester
                            student["Section"] = section
                            student["CollegeID"] = college_id

                            timetable_data = []

                            if os.path.exists("timetable.csv"):

                                tt = pd.read_csv("timetable.csv").fillna("-")

                                tt["Department"] = (
                                    tt["Department"]
                                    .astype(str)
                                    .str.strip()
                                    .str.upper()
                                )

                                tt["Semester"] = (
                                    tt["Semester"]
                                    .astype(str)
                                    .str.replace(".0", "", regex=False)
                                    .str.strip()
                                )

                                tt["Section"] = (
                                    tt["Section"]
                                    .astype(str)
                                    .str.strip()
                                    .str.upper()
                                )

                                filtered_tt = tt[
                                    (tt["Department"] == str(department).strip().upper()) &
                                    (tt["Semester"] == str(semester).strip()) &
                                    (tt["Section"] == str(section).strip().upper())
                                ]

                                timetable_data = filtered_tt.to_dict(orient="records")

                            return render_template(
                                "student_dashboard.html",
                                student=student,
                                timetable=timetable_data
                            )

    return redirect("/student_portal")

@app.route("/college_registration")
def college_registration_page():
    return render_template("college_registration.html")

@app.route("/submit_college_request", methods=["POST"])
def submit_request():
    data = request.get_json()
    pending = load_pending()
    data['request_id'] = random.randint(1000, 9999)
    data['status'] = "Pending"
    data['date'] = datetime.now().strftime("%Y-%m-%d")
    pending.append(data)    
    with open(PENDING_COLLEGES_FILE, "w") as f:
        json.dump(pending, f, indent=4)   
    return jsonify({"success": True, "message": "Request submitted successfully!"})

@app.route("/get_approved_colleges")
def get_approved():
    colleges = load_colleges()
    list_format = []
    for college_id, data in colleges.items():
        if isinstance(data, dict):
            list_format.append({
                "id": college_id,
                "name": data.get("name", "-"),
                "admin_username": data.get("admin_username", "-"),
                "admin_password": data.get("admin_password", "-")
            })
        else:
            list_format.append({
                "id": college_id,
                "name": data,
                "admin_username": "-",
                "admin_password": "-"
            })
    return jsonify(list_format)

@app.route("/get_teachers")
def get_teachers():
    teachers = []
    college_id = session.get("college_id")

    if os.path.exists("registered_teachers.txt"):
        with open("registered_teachers.txt", "r") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                if college_id and f"CollegeID: {college_id}" not in line:
                    continue

                try:
                    parts = line.split(" | ")
                    name = parts[1].replace("Name: ", "").strip()
                    username = parts[3].replace("User: ", "").strip()

                    teachers.append({
                        "name": name,
                        "username": username
                    })

                except:
                    continue

    return jsonify(teachers)

@app.route("/manage_colleges")
def manage_colleges():
    return render_template("manage_colleges.html")

@app.route("/get_pending_requests")
def get_pending():
    return jsonify(load_pending())

@app.route("/approve_college", methods=["POST"])
def approve_college():
    data = request.get_json()
    req_id = data.get("request_id")
    college_name = data.get("name")
    prefix = college_name.replace(" ", "").upper()[:4]
    unique_id = f"{prefix}_{random.randint(1000, 9999)}"
    admin_username = unique_id + "_admin"
    admin_password = unique_id + "Admin"
    colleges = load_colleges()
    colleges[unique_id] = {
    "name": college_name,
    "admin_username": admin_username,
    "admin_password": admin_password
}
    with open(COLLEGE_DATA_FILE, "w") as f:
        json.dump(colleges, f, indent=4)
    pending = load_pending()
    updated_pending = [p for p in pending if p.get('request_id') != req_id]
    with open(PENDING_COLLEGES_FILE, "w") as f:
        json.dump(updated_pending, f, indent=4)
    return jsonify({
    "success": True,
    "college_id": unique_id,
    "admin_username": admin_username,
    "admin_password": admin_password
})

@app.route("/end_attendance", methods=["POST"])
def end_attendance():
    global camera_process
    if camera_process:
        camera_process.terminate()
        camera_process = None
    data = request.get_json()
    department = data.get("department", "").strip().upper()
    semester = data.get("semester", "").strip()
    section = data.get("section", "").strip().upper()
    subject = data.get("subject", "").strip()
    today = datetime.now().strftime("%Y-%m-%d")
    attendance_file = "attendance.csv"
    student_file = os.path.join(
        "college_data",
        department,
        semester,
        section,
        "student_details.csv"
    )
    if not os.path.exists(student_file):
        return jsonify({
            "success": False,
            "message": "Student file not found",
            "absent_students": []
        })
    students_df = pd.read_csv(student_file).fillna("-")
    students_df["ID"] = students_df["ID"].astype(str).str.replace(".0", "", regex=False).str.strip()
    if os.path.exists(attendance_file):
        df = pd.read_csv(attendance_file).fillna("-")
    else:
        df = pd.DataFrame(
            columns=[
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
    for col in ["Department", "Semester", "Section", "Subject"]:
        if col not in df.columns:
            df[col] = "-"
    df["ID"] = df["ID"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Department"] = df["Department"].astype(str).str.strip().str.upper()
    df["Semester"] = df["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Section"] = df["Section"].astype(str).str.strip().str.upper()
    df["Subject"] = df["Subject"].astype(str).str.strip()
    df["Date"] = df["Date"].astype(str).str.strip()
    df["Status"] = df["Status"].astype(str).str.strip()
    today_present_ids = df[
        (df["Department"] == department) &
        (df["Semester"] == semester) &
        (df["Section"] == section) &
        (df["Subject"] == subject) &
        (df["Date"] == today) &
        (df["Status"].str.lower() == "present")
    ]["ID"].tolist()
    absent_students = []
    for _, student in students_df.iterrows():
        student_id = str(student["ID"]).strip()
        name = str(student["Name"]).strip()
        if student_id not in today_present_ids:
            already_marked = df[
                (df["ID"] == student_id) &
                (df["Department"] == department) &
                (df["Semester"] == semester) &
                (df["Section"] == section) &
                (df["Subject"] == subject) &
                (df["Date"] == today)
            ]
            if already_marked.empty:
                new_row = pd.DataFrame(
                    [[
                        name,
                        student_id,
                        department,
                        semester,
                        section,
                        subject,
                        today,
                        "-",
                        "Absent"
                    ]],
                    columns=[
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
            absent_students.append({
                "Name": name,
                "ID": student_id
            })
    df = df.drop_duplicates(
        subset=[
            "ID",
            "Department",
            "Semester",
            "Section",
            "Subject",
            "Date"
        ],
        keep="first"
    )
    df.to_csv(attendance_file, index=False)
    return jsonify({
        "success": True,
        "message": "Attendance ended",
        "absent_students": absent_students
    })

@app.route("/get_all_students")
def get_all_students():
    teacher_username = session.get("username")
    department = request.args.get("department", "").strip().upper()
    semester = request.args.get("semester", "").strip().replace(".0", "")
    section = request.args.get("section", "").strip().upper()
    if not teacher_username:
        return jsonify([])
    assignments_file = "teacher_assignments.csv"
    if not os.path.exists(assignments_file):
        return jsonify([])
    assignments = pd.read_csv(assignments_file).fillna("")
    assignments["TeacherUsername"] = assignments["TeacherUsername"].astype(str).str.strip()
    assignments["Department"] = assignments["Department"].astype(str).str.strip().str.upper()
    assignments["Semester"] = assignments["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    assignments["Section"] = assignments["Section"].astype(str).str.strip().str.upper()
    allowed = assignments[
        (assignments["TeacherUsername"] == str(teacher_username).strip()) &
        (assignments["Department"] == department) &
        (assignments["Semester"] == semester) &
        (assignments["Section"] == section)
    ]
    if allowed.empty:
        return jsonify([])
    college_id = session.get("college_id")

    if not college_id:
        assignments_file = "teacher_assignments.csv"
        if os.path.exists(assignments_file):
            assignments = pd.read_csv(assignments_file).fillna("")
            matched = assignments[
                assignments["TeacherUsername"].astype(str).str.strip() == str(teacher_username).strip()
            ]
            if not matched.empty and "CollegeID" in matched.columns:
                college_id = matched.iloc[0]["CollegeID"]

    student_file = os.path.join(
        "college_data",
        college_id,
        department,
        semester,
        section,
        "student_details.csv"
    )
    if not os.path.exists(student_file):
        return jsonify([])
    students = pd.read_csv(student_file).fillna("-")
    return jsonify(students.to_dict(orient="records"))

@app.route("/get_performance_students")
def get_performance_students():
    teacher_username = session.get("username")
    department = request.args.get("department", "").strip().upper()
    semester = request.args.get("semester", "").strip()
    section = request.args.get("section", "").strip().upper()
    subject = request.args.get("subject", "").strip()
    assignments_file = "teacher_assignments.csv"
    if not teacher_username:
        return jsonify([])
    if not os.path.exists(assignments_file):
        return jsonify([])
    assignments = pd.read_csv(assignments_file).fillna("")
    assignments["TeacherUsername"] = assignments["TeacherUsername"].astype(str).str.strip()
    assignments["Department"] = assignments["Department"].astype(str).str.strip().str.upper()
    assignments["Semester"] = assignments["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    assignments["Section"] = assignments["Section"].astype(str).str.strip().str.upper()
    assignments["Subject"] = assignments["Subject"].astype(str).str.strip()
    allowed = assignments[
        (assignments["TeacherUsername"] == teacher_username) &
        (assignments["Department"] == department) &
        (assignments["Semester"] == semester) &
        (assignments["Section"] == section) &
        (assignments["Subject"] == subject)
    ]
    if allowed.empty:
        return jsonify([])
    student_file = os.path.join(
        "college_data",
        department,
        semester,
        section,
        "student_details.csv"
    )
    attendance_file = "attendance.csv"
    if not os.path.exists(student_file):
        return jsonify([])
    students_df = pd.read_csv(student_file).fillna("-")
    if os.path.exists(attendance_file):
        attendance_df = pd.read_csv(attendance_file)
    else:
        attendance_df = pd.DataFrame(columns=["Name", "ID", "Date", "Time", "Status"])
    today = datetime.now()
    current_month = today.strftime("%Y-%m")
    month_attendance = attendance_df[
        attendance_df["Date"].astype(str).str.startswith(current_month)
    ]
    holiday_dates = set()
    if os.path.exists("holidays.csv"):
        holidays_df = pd.read_csv("holidays.csv")
        holiday_dates = set(holidays_df["Date"].astype(str).tolist())
    working_days = 0
    for day in range(1, today.day + 1):
        d = today.replace(day=day)
        date_str = d.strftime("%Y-%m-%d")
        if d.weekday() == 6:
            continue
        if d.weekday() == 5:
            saturday_number = (day - 1) // 7 + 1
            if saturday_number == 2 or saturday_number == 4:
                continue
        if date_str in holiday_dates:
            continue
        working_days += 1
    result = []
    for _, student in students_df.iterrows():
        student_id = str(student["ID"])
        attended_days = month_attendance[
            (month_attendance["ID"].astype(str) == student_id) &
            (month_attendance["Status"].astype(str) == "Present")
        ]["Date"].nunique()
        attendance_percentage = round((attended_days / working_days) * 100, 2) if working_days > 0 else 0
        attendance_marks = round((attendance_percentage / 100) * 5, 2)
        result.append({
            "Name": student["Name"],
            "ID": student["ID"],
            "attended_days": int(attended_days),
            "working_days": working_days,
            "attendance_percentage": attendance_percentage,
            "attendance_marks": attendance_marks
        })
    return jsonify(result)

@app.route("/admin_register_student")
def admin_register_student():
    name = request.args.get("name", "")
    student_id = request.args.get("id", "")
    phone = request.args.get("phone", "")
    p_name = request.args.get("p_name", "")
    p_phone = request.args.get("p_phone", "")
    gender = request.args.get("gender", "")
    department = request.args.get("department", "")
    semester = request.args.get("semester", "")
    section = request.args.get("section", "")

    if not name or not student_id or not department or not semester or not section:
        return jsonify({
            "success": False,
            "message": "Missing required student details"
        }), 400
    college_id = session.get("college_id")

    base_path = os.path.join(
        "college_data",
        college_id,
        department,
        semester,
        section
    )
    os.makedirs(base_path, exist_ok=True)
    subprocess.Popen([
        sys.executable,
        "register_student.py",
        name,
        student_id,
        phone,
        p_name,
        p_phone,
        gender,
        department,
        semester,
        section,
        base_path
    ])
    return jsonify({"success": True})

@app.route("/admin_all_students")
def admin_all_students():
    if not session.get("college_admin"):
        return jsonify([]), 401
    all_students = []
    college_id = session.get("college_id")

    base_folder = os.path.join(
        "college_data",
        college_id
    )
    if not os.path.exists(base_folder):
        return jsonify([])
    for department in os.listdir(base_folder):
        dept_path = os.path.join(base_folder, department)
        if not os.path.isdir(dept_path):
            continue
        for semester in os.listdir(dept_path):
            sem_path = os.path.join(dept_path, semester)
            if not os.path.isdir(sem_path):
                continue
            for section in os.listdir(sem_path):
                section_path = os.path.join(sem_path, section)
                if not os.path.isdir(section_path):
                    continue
                student_file = os.path.join(section_path, "student_details.csv")
                if os.path.exists(student_file):
                    try:
                        df = pd.read_csv(student_file)
                        df = df.fillna("-")
                        for _, row in df.iterrows():
                            student = row.to_dict()
                            student["Department"] = department
                            student["Semester"] = semester
                            student["Section"] = section
                            all_students.append(student)
                    except Exception as e:
                        print("Error reading:", student_file, e)
    return jsonify(all_students)    

@app.route("/get_teacher_assigned_classes")
def get_teacher_assigned_classes():
    teacher_username = session.get("username")
    if not teacher_username:
        return jsonify([]), 401
    assignment_file = "teacher_assignments.csv"
    timetable_file = "timetable.csv"
    timings_file = "timings.csv"
    if not os.path.exists(assignment_file):
        return jsonify([])
    assignments = pd.read_csv(assignment_file).fillna("")
    assignments["TeacherUsername"] = assignments["TeacherUsername"].astype(str).str.strip()
    assignments["Department"] = assignments["Department"].astype(str).str.strip().str.upper()
    assignments["Semester"] = assignments["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    assignments["Section"] = assignments["Section"].astype(str).str.strip().str.upper()
    assignments["Subject"] = assignments["Subject"].astype(str).str.strip()
    if "Status" in assignments.columns:
        assignments = assignments[
            assignments["Status"].astype(str).str.lower() != "inactive"
        ]
    assigned = assignments[
        assignments["TeacherUsername"] == str(teacher_username).strip()
    ]
    if assigned.empty:
        return jsonify([])
    timings = {}
    if os.path.exists(timings_file):
        timings_df = pd.read_csv(timings_file).fillna("")
        timings = timings_df.iloc[0].to_dict()
    timetable = pd.DataFrame()

    if os.path.exists(timetable_file):
        timetable = pd.read_csv(timetable_file).fillna("")
        timetable["Department"] = timetable["Department"].astype(str).str.strip().str.upper()
        timetable["Semester"] = timetable["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
        timetable["Section"] = timetable["Section"].astype(str).str.strip().str.upper()
    result = []
    for _, row in assigned.iterrows():
        schedule = []

        if not timetable.empty:
            class_rows = timetable[
                (timetable["Department"] == row["Department"]) &
                (timetable["Semester"] == row["Semester"]) &
                (timetable["Section"] == row["Section"])
            ]
            for _, trow in class_rows.iterrows():
                day = str(trow["Day"]).strip()
                for col in timetable.columns:
                    if col.startswith("Sub"):
                        subject_in_slot = str(trow[col]).strip()
                        if subject_in_slot.lower() == row["Subject"].lower():
                            schedule.append({
                                "day": day,
                                "period": col,
                                "time": timings.get(col, "")
                            })
        result.append({
            "department": row["Department"],
            "semester": row["Semester"],
            "section": row["Section"],
            "subject": row["Subject"],
            "schedule": schedule
        })
    return jsonify(result)

@app.route("/get_subjects")
def get_subjects():
    department = request.args.get("department", "").strip().upper()
    semester = request.args.get("semester", "").strip()
    section = request.args.get("section", "").strip().upper()
    timetable_file = "timetable.csv"
    assignment_file = "teacher_assignments.csv"
    if not os.path.exists(timetable_file):
        return jsonify([])
    timetable_df = pd.read_csv(timetable_file)
    timetable_df = timetable_df.fillna("")
    timetable_df["Department"] = timetable_df["Department"].astype(str).str.strip().str.upper()
    timetable_df["Semester"] = timetable_df["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    timetable_df["Section"] = timetable_df["Section"].astype(str).str.strip().str.upper()
    class_rows = timetable_df[
        (timetable_df["Department"] == department) &
        (timetable_df["Semester"] == semester) &
        (timetable_df["Section"] == section)
    ]
    subjects = []
    for _, row in class_rows.iterrows():
        for col in timetable_df.columns:
            if col.startswith("Sub"):
                sub = str(row[col]).strip()
                if sub and sub.lower() != "break":
                    subjects.append(sub)
    subjects = sorted(list(set(subjects)))
    assigned_subjects = []
    if os.path.exists(assignment_file):
        assign_df = pd.read_csv(assignment_file)
        assign_df = assign_df.fillna("")
        assign_df["Department"] = assign_df["Department"].astype(str).str.strip().str.upper()
        assign_df["Semester"] = assign_df["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
        assign_df["Section"] = assign_df["Section"].astype(str).str.strip().str.upper()
        assign_df["Subject"] = assign_df["Subject"].astype(str).str.strip()
        if "Status" in assign_df.columns:
            assign_df["Status"] = assign_df["Status"].astype(str).str.strip()
            assign_df = assign_df[assign_df["Status"].str.lower() != "inactive"]
        assigned_subjects = assign_df[
            (assign_df["Department"] == department) &
            (assign_df["Semester"] == semester) &
            (assign_df["Section"] == section)
        ]["Subject"].tolist()
    available_subjects = [
        sub for sub in subjects
        if sub not in assigned_subjects
    ]
    return jsonify(available_subjects)

@app.route("/upload_timetable", methods=["POST"])
def upload_timetable():
    department = request.form.get("department", "").strip().upper()
    semester = request.form.get("semester", "").strip()
    section = request.form.get("section", "").strip().upper()
    college_id = session.get("college_id")
    if not department or not semester or not section:
        return jsonify({
            "success": False,
            "message": "Please select department, semester and section"
        })
    if "file" not in request.files:
        return jsonify({
            "success": False,
            "message": "No file selected"
        })
    file = request.files["file"]
    if file.filename == "":
        return jsonify({
            "success": False,
            "message": "Please choose a CSV file"
        })
    new_df = pd.read_csv(file)
    new_df = new_df.fillna("")
    new_df["Department"] = department
    new_df["Semester"] = semester
    new_df["Section"] = section
    new_df["CollegeID"] = college_id
    final_columns = [
    "CollegeID", "Day", "Department", "Semester", "Section",
    "Sub1", "Sub2", "Sub3", "Sub4", "Sub5", "Sub6"
]
    new_df = new_df[final_columns]
    file_path = "timetable.csv"
    if os.path.exists(file_path):
        old_df = pd.read_csv(file_path)
        old_df = old_df.fillna("")
        old_df = old_df[
            ~(
                (old_df["Department"].astype(str).str.upper() == department) &
                (old_df["Semester"].astype(str) == semester) &
                (old_df["Section"].astype(str).str.upper() == section)
            )
        ]
        final_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        final_df = new_df
    final_df.to_csv(file_path, index=False)
    return jsonify({
        "success": True,
        "message": "Timetable uploaded successfully"
    })
    
@app.route("/upload_period_timings", methods=["POST"])
def upload_period_timings():

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "message": "No file selected"
        })
    file = request.files["file"]

    if file.filename == "":
        return jsonify({
            "success": False,
            "message": "Please choose a CSV file"
        })
    file.save("timings.csv")
    return jsonify({
        "success": True,
        "message": "Period timings uploaded successfully"
    })

@app.route("/get_subject_schedule")
def get_subject_schedule():
    department = request.args.get("department")
    semester = request.args.get("semester")
    section = request.args.get("section")
    subject = request.args.get("subject")
    if not os.path.exists("timetable.csv"):
        return jsonify([])
    if not os.path.exists("timings.csv"):
        return jsonify([])
    timetable_df = pd.read_csv("timetable.csv")
    timings_df = pd.read_csv("timings.csv")
    timings = timings_df.iloc[0].to_dict()
    timetable_df = timetable_df.fillna("")
    filtered = timetable_df[
        (timetable_df["Department"].astype(str).str.upper() == str(department).upper()) &
        (timetable_df["Semester"].astype(str) == str(semester)) &
        (timetable_df["Section"].astype(str).str.upper() == str(section).upper())
    ]
    schedule = []
    for _, row in filtered.iterrows():
        day = row["Day"]
        for col in timetable_df.columns:
            if col.startswith("Sub"):
                cell_subject = str(row[col]).strip()
                if cell_subject.lower() == str(subject).strip().lower():
                    schedule.append({
                        "day": day,
                        "period": col,
                        "time": timings.get(col, "")
                    })
    return jsonify(schedule)

@app.route("/get_student_timetable")
def get_student_timetable():
    student_id = session.get("student_id")
    if not student_id:
        return jsonify([]), 401
    if not os.path.exists("timetable.csv"):
        return jsonify([])
    base_folder = "college_data"
    student_class = None
    for department in os.listdir(base_folder):
        dept_path = os.path.join(base_folder, department)
        if not os.path.isdir(dept_path):
            continue
        for semester in os.listdir(dept_path):
            sem_path = os.path.join(dept_path, semester)
            if not os.path.isdir(sem_path):
                continue
            for section in os.listdir(sem_path):
                section_path = os.path.join(sem_path, section)
                if not os.path.isdir(section_path):
                    continue
                student_file = os.path.join(section_path, "student_details.csv")
                if os.path.exists(student_file):
                    df = pd.read_csv(student_file).fillna("")
                    matched = df[
                        df["ID"].astype(str).str.strip() == str(student_id).strip()
                    ]
                    if not matched.empty:
                        student_class = {
                            "department": department.strip().upper(),
                            "semester": semester.strip(),
                            "section": section.strip().upper()
                        }
                        break
            if student_class:
                break
        if student_class:
            break
    print("Logged student ID:", student_id)
    print("Found student class:", student_class)
    if not student_class:
        return jsonify([])
    timetable = pd.read_csv("timetable.csv").fillna("")
    timetable["Department"] = timetable["Department"].astype(str).str.strip().str.upper()
    timetable["Semester"] = timetable["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    timetable["Section"] = timetable["Section"].astype(str).str.strip().str.upper()
    print("Timetable data:")
    print(timetable[["Day", "Department", "Semester", "Section"]])
    print("Searching for:")
    print(student_class)
    filtered = timetable[
        (timetable["Department"] == student_class["department"]) &
        (timetable["Semester"] == student_class["semester"]) &
        (timetable["Section"] == student_class["section"])
    ]
    print("Filtered timetable:")
    print(filtered)
    return jsonify(filtered.to_dict(orient="records"))

@app.route("/admin_delete_student", methods=["POST"])
def admin_delete_student():
    if not session.get("college_admin"):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json()
    student_id = str(data.get("student_id", "")).strip()
    department = str(data.get("department", "")).strip().upper()
    semester = str(data.get("semester", "")).strip()
    section = str(data.get("section", "")).strip().upper()
    if not student_id or not department or not semester or not section:
        return jsonify({
            "success": False,
            "message": "Missing student/class details"
        }), 400
    college_id = session.get("college_id")

    class_folder = os.path.join(
        "college_data",
        college_id,
        department,
        semester,
        section
    )
    student_file = os.path.join(class_folder, "student_details.csv")
    dataset_folder = os.path.join(class_folder, "dataset")
    if not os.path.exists(student_file):
        return jsonify({
            "success": False,
            "message": "Student file not found"
        }), 404
    df = pd.read_csv(student_file).fillna("")
    matched = df[df["ID"].astype(str).str.strip() == student_id]
    if matched.empty:
        return jsonify({
            "success": False,
            "message": "Student not found"
        }), 404
    student_name = str(matched.iloc[0]["Name"]).strip().replace(" ", "_")
    df = df[df["ID"].astype(str).str.strip() != student_id]
    df.to_csv(student_file, index=False)
    import shutil
    # Delete face dataset folder safely by student ID
    if os.path.exists(dataset_folder):
        for folder in os.listdir(dataset_folder):
            folder_path = os.path.join(dataset_folder, folder)

            if os.path.isdir(folder_path) and folder.endswith("_" + student_id):
                shutil.rmtree(folder_path)
        model_file = os.path.join(
        "college_data",
        college_id,
        "trainer.yml"
    )

    label_file = os.path.join(
        "college_data",
        college_id,
        "labels.npy"
    )

    if os.path.exists(model_file):
        os.remove(model_file)

    if os.path.exists(label_file):
        os.remove(label_file)    
    return jsonify({
        "success": True,
        "message": "Student deleted successfully"
    })

@app.route("/student_attendance_data")
def student_attendance_data():
    student_id = str(session.get("student_id", "")).strip()

    if not student_id:
        return jsonify([]), 401

    attendance_file = "attendance.csv"

    if not os.path.exists(attendance_file):
        return jsonify([])

    student_name = ""
    student_class = None
    base_folder = "college_data"

    for college_id in os.listdir(base_folder):
        college_path = os.path.join(base_folder, college_id)

        if not os.path.isdir(college_path):
            continue

        for department in os.listdir(college_path):
            dept_path = os.path.join(college_path, department)

            if not os.path.isdir(dept_path):
                continue

            for semester in os.listdir(dept_path):
                sem_path = os.path.join(dept_path, semester)

                if not os.path.isdir(sem_path):
                    continue

                for section in os.listdir(sem_path):
                    section_path = os.path.join(sem_path, section)

                    if not os.path.isdir(section_path):
                        continue

                    student_file = os.path.join(section_path, "student_details.csv")

                    if os.path.exists(student_file):
                        sdf = pd.read_csv(student_file).fillna("")
                        sdf["ID"] = sdf["ID"].astype(str).str.replace(".0", "", regex=False).str.strip()

                        matched = sdf[sdf["ID"] == student_id]

                        if not matched.empty:
                            student_name = str(matched.iloc[0]["Name"]).strip()
                            student_class = {
                                "college_id": college_id,
                                "department": department.strip().upper(),
                                "semester": semester.strip(),
                                "section": section.strip().upper()
                            }
                            break

                if student_class:
                    break

            if student_class:
                break

        if student_class:
            break

    if not student_class:
        return jsonify([])

    df = pd.read_csv(attendance_file).fillna("-")

    for col in ["ID", "Name", "Department", "Semester", "Section", "Subject", "Status"]:
        if col not in df.columns:
            df[col] = "-"

    df["ID"] = df["ID"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Name"] = df["Name"].astype(str).str.strip()
    df["Department"] = df["Department"].astype(str).str.strip().str.upper()
    df["Semester"] = df["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Section"] = df["Section"].astype(str).str.strip().str.upper()

    student_records = df[
        (df["ID"] == student_id) &
        (df["Department"] == student_class["department"]) &
        (df["Semester"] == student_class["semester"]) &
        (df["Section"] == student_class["section"])
    ]

    if student_records.empty:
        return jsonify([])

    summary = []

    for subject, group in student_records.groupby("Subject"):
        present_count = len(group[group["Status"].astype(str).str.lower() == "present"])
        absent_count = len(group[group["Status"].astype(str).str.lower() == "absent"])

        total_classes = present_count + absent_count
        percentage = round((present_count / total_classes) * 100, 2) if total_classes > 0 else 0
        status = "Shortage" if percentage <= 75 else "Safe"

        summary.append({
            "Subject": subject,
            "TotalClasses": int(total_classes),
            "Attended": int(present_count),
            "Absent": int(absent_count),
            "Percentage": percentage,
            "Status": status
        })

    return jsonify(summary)

@app.route("/available_timetable_options")
def available_timetable_options():
    college_id = session.get("college_id")

    departments = ["BCA", "BBA", "BCom", "MBA"]
    semesters = ["1", "2", "3", "4", "5", "6"]
    sections = ["A", "B", "C"]

    uploaded = set()

    if os.path.exists("timetable.csv"):
        df = pd.read_csv("timetable.csv").fillna("")

        if "CollegeID" in df.columns:
            df = df[df["CollegeID"].astype(str).str.strip() == str(college_id).strip()]
        else:
            df = pd.DataFrame()

        if not df.empty:
            df["Department"] = df["Department"].astype(str).str.strip().str.upper()
            df["Semester"] = df["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
            df["Section"] = df["Section"].astype(str).str.strip().str.upper()

            for _, row in df.iterrows():
                uploaded.add((row["Department"], row["Semester"], row["Section"]))

    result = {}

    for dept in departments:
        result[dept] = {}

        for sem in semesters:
            available_sections = []

            for sec in sections:
                if (dept, sem, sec) not in uploaded:
                    available_sections.append(sec)

            if available_sections:
                result[dept][sem] = available_sections

        if not result[dept]:
            del result[dept]

    return jsonify(result)

@app.route("/uploaded_timetable_options")
def uploaded_timetable_options():
    result = {}

    if not os.path.exists("timetable.csv"):
        return jsonify(result)

    df = pd.read_csv("timetable.csv").fillna("")
    college_id = session.get("college_id")

    college_id = session.get("college_id")

    if "CollegeID" not in df.columns:
        return jsonify([])

    df["CollegeID"] = df["CollegeID"].astype(str).str.strip()
    df = df[df["CollegeID"] == str(college_id).strip()]

    df["Department"] = df["Department"].astype(str).str.strip().str.upper()
    df["Semester"] = df["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Section"] = df["Section"].astype(str).str.strip().str.upper()

    for _, row in df.iterrows():
        dept = row["Department"]
        sem = row["Semester"]
        sec = row["Section"]

        if dept not in result:
            result[dept] = {}

        if sem not in result[dept]:
            result[dept][sem] = []

        if sec not in result[dept][sem]:
            result[dept][sem].append(sec)

    return jsonify(result)

@app.route("/view_timetables")
def view_timetables():
    department = request.args.get("department", "").strip().upper()
    semester = request.args.get("semester", "").strip()
    section = request.args.get("section", "").strip().upper()
    if not os.path.exists("timetable.csv"):
        return jsonify([])
    df = pd.read_csv("timetable.csv").fillna("-")
    college_id = session.get("college_id")

    college_id = session.get("college_id")

    if "CollegeID" not in df.columns:
        return jsonify([])

    df["CollegeID"] = df["CollegeID"].astype(str).str.strip()
    df = df[df["CollegeID"] == str(college_id).strip()]
    df["Department"] = df["Department"].astype(str).str.strip().str.upper()
    df["Semester"] = df["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Section"] = df["Section"].astype(str).str.strip().str.upper()

    filtered = df[
        (df["Department"] == department) &
        (df["Semester"] == semester) &
        (df["Section"] == section)
    ]
    return jsonify(filtered.to_dict(orient="records"))

@app.route("/update_timetable_cell", methods=["POST"])
def update_timetable_cell():
    data = request.get_json()
    department = data.get("department")
    semester = data.get("semester")
    section = data.get("section")
    day = data.get("day")
    column = data.get("column")
    value = data.get("value")
    if not os.path.exists("timetable.csv"):
        return jsonify({"success": False, "message": "Timetable file not found"})
    df = pd.read_csv("timetable.csv").fillna("")
    condition = (
        (df["Department"].astype(str) == str(department)) &
        (df["Semester"].astype(str) == str(semester)) &
        (df["Section"].astype(str) == str(section)) &
        (df["Day"].astype(str) == str(day))
    )
    if column not in df.columns:
        return jsonify({"success": False, "message": "Invalid column"})
    df.loc[condition, column] = value
    df.to_csv("timetable.csv", index=False)
    return jsonify({"success": True, "message": "Timetable updated"})

@app.route("/save_full_timetable_edit", methods=["POST"])
def save_full_timetable_edit():
    updated_rows = request.get_json()
    if not updated_rows:
        return jsonify({
            "success": False,
            "message": "No timetable data received"
        })
    if not os.path.exists("timetable.csv"):
        return jsonify({
            "success": False,
            "message": "Timetable file not found"
        })
    df = pd.read_csv("timetable.csv").fillna("")
    first = updated_rows[0]
    department = str(first["Department"]).strip().upper()
    semester = str(first["Semester"]).strip()
    section = str(first["Section"]).strip().upper()
    df["Department"] = df["Department"].astype(str).str.strip().str.upper()
    df["Semester"] = df["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Section"] = df["Section"].astype(str).str.strip().str.upper()
    df = df[
        ~(
            (df["Department"] == department) &
            (df["Semester"] == semester) &
            (df["Section"] == section)
        )
    ]
    updated_df = pd.DataFrame(updated_rows)
    final_df = pd.concat([df, updated_df], ignore_index=True)
    final_df.to_csv("timetable.csv", index=False)
    return jsonify({
        "success": True,
        "message": "Timetable updated successfully"
    })

@app.route("/save_internal_marks", methods=["POST"])
def save_internal_marks():
    data = request.get_json()
    teacher = session.get("username", "")
    row = {
        "Teacher": teacher,
        "StudentID": data.get("student_id"),
        "Name": data.get("name"),
        "Department": data.get("department"),
        "Semester": data.get("semester"),
        "Section": data.get("section"),
        "Subject": data.get("subject"),
        "I1_Test": data.get("i1_test", 0),
        "I1_Assignment": data.get("i1_assignment", 0),
        "I2_Test": data.get("i2_test", 0),
        "I2_Assignment": data.get("i2_assignment", 0)
    }
    file_path = "internal_marks.csv"
    new_df = pd.DataFrame([row])
    if os.path.exists(file_path):
        old_df = pd.read_csv(file_path).fillna("")
        old_df = old_df[
            ~(
                (old_df["StudentID"].astype(str) == str(row["StudentID"])) &
                (old_df["Subject"].astype(str) == str(row["Subject"])) &
                (old_df["Department"].astype(str) == str(row["Department"])) &
                (old_df["Semester"].astype(str) == str(row["Semester"])) &
                (old_df["Section"].astype(str) == str(row["Section"]))
            )
        ]
        final_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        final_df = new_df
    final_df.to_csv(file_path, index=False)
    return jsonify({
        "success": True,
        "message": "Internal marks saved successfully"
    })

@app.route("/student_internal_marks")
def student_internal_marks():
    student_id = str(session.get("student_id", "")).strip()
    if not student_id:
        return jsonify([])
    student_class = None
    base_folder = "college_data"
    for department in os.listdir(base_folder):
        dept_path = os.path.join(base_folder, department)
        if not os.path.isdir(dept_path):
            continue
        for semester in os.listdir(dept_path):
            sem_path = os.path.join(dept_path, semester)
            if not os.path.isdir(sem_path):
                continue
            for section in os.listdir(sem_path):
                section_path = os.path.join(sem_path, section)
                student_file = os.path.join(section_path, "student_details.csv")
                if os.path.exists(student_file):
                    sdf = pd.read_csv(student_file).fillna("")
                    sdf["ID"] = sdf["ID"].astype(str).str.replace(".0", "", regex=False).str.strip()
                    matched = sdf[sdf["ID"] == student_id]
                    if not matched.empty:
                        student_class = {
                            "department": department.strip().upper(),
                            "semester": semester.strip(),
                            "section": section.strip().upper()
                        }
                        break
            if student_class:
                break
        if student_class:
            break
    if not student_class:
        return jsonify([])
    subjects = []
    if os.path.exists("timetable.csv"):
        tt = pd.read_csv("timetable.csv").fillna("")
        tt["Department"] = tt["Department"].astype(str).str.strip().str.upper()
        tt["Semester"] = tt["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
        tt["Section"] = tt["Section"].astype(str).str.strip().str.upper()
        class_tt = tt[
            (tt["Department"] == student_class["department"]) &
            (tt["Semester"] == student_class["semester"]) &
            (tt["Section"] == student_class["section"])
        ]
        for _, row in class_tt.iterrows():
            for col in class_tt.columns:
                if col.startswith("Sub"):
                    subject = str(row[col]).strip()
                    if subject and subject != "-" and subject.lower() != "break":
                        subjects.append(subject)
    subjects = sorted(list(set(subjects)))
    marks_df = pd.DataFrame()

    if os.path.exists("internal_marks.csv"):
        marks_df = pd.read_csv("internal_marks.csv").fillna("")
        marks_df["StudentID"] = marks_df["StudentID"].astype(str).str.strip()
        marks_df["Subject"] = marks_df["Subject"].astype(str).str.strip()
    result = []
    all_i1_done = True
    all_i2_done = True
    for subject in subjects:
        row = None
        if not marks_df.empty:
            matched_marks = marks_df[
                (marks_df["StudentID"] == student_id) &
                (marks_df["Subject"].str.lower() == subject.lower())
            ]
            if not matched_marks.empty:
                row = matched_marks.iloc[0]
        i1_test = float(row.get("I1_Test", 0) or 0) if row is not None else 0
        i1_assignment = float(row.get("I1_Assignment", 0) or 0) if row is not None else 0
        i2_test = float(row.get("I2_Test", 0) or 0) if row is not None else 0
        i2_assignment = float(row.get("I2_Assignment", 0) or 0) if row is not None else 0
        if i1_test == 0 and i1_assignment == 0:
            all_i1_done = False
        if i2_test == 0 and i2_assignment == 0:
            all_i2_done = False
        attendance_percentage = 100
        if os.path.exists("attendance.csv"):
            att_df = pd.read_csv("attendance.csv").fillna("-")
            for col in ["ID", "Subject", "Status"]:
                if col not in att_df.columns:
                    att_df[col] = "-"
            att_df["ID"] = att_df["ID"].astype(str).str.strip()
            att_df["Subject"] = att_df["Subject"].astype(str).str.strip()
            student_att = att_df[
                (att_df["ID"] == student_id) &
                (att_df["Subject"].str.lower() == subject.lower())
            ]
            if not student_att.empty:
                present_count = len(
                    student_att[
                        student_att["Status"].astype(str).str.lower() == "present"
                    ]
                )
                absent_count = len(
                    student_att[
                        student_att["Status"].astype(str).str.lower() == "absent"
                    ]
                )
                attendance_percentage = 100 + present_count - (absent_count * 3)

                if attendance_percentage > 100:
                    attendance_percentage = 100

                if attendance_percentage < 0:
                    attendance_percentage = 0
        if attendance_percentage > 90:
            attendance_marks = 5
        elif attendance_percentage >= 80:
            attendance_marks = 4
        elif attendance_percentage >= 75:
            attendance_marks = 3
        elif attendance_percentage >= 70:
            attendance_marks = 2
        else:
            attendance_marks = 1
        internal1 = (i1_test / 3) + i1_assignment + attendance_marks
        internal2 = (i2_test / 3) + i2_assignment + attendance_marks
        if i2_test > 0 or i2_assignment > 0:
            final_internal = internal1 + internal2
        else:
            final_internal = ""
        result.append({
            "Subject": subject,
            "I1_Test": i1_test,
            "I1_Assignment": i1_assignment,
            "Internal1": round(internal1, 2),
            "I2_Test": i2_test,
            "I2_Assignment": i2_assignment,
            "Internal2": round(internal2, 2),
            "AttendancePercentage": attendance_percentage,
            "AttendanceMarks": attendance_marks,
            "FinalInternal": final_internal if final_internal == "" else round(final_internal, 2)
        })
    return jsonify(result)

@app.route("/student_attendance_data_all")
def student_attendance_data_all():
    department = request.args.get("department", "").strip().upper()
    semester = request.args.get("semester", "").strip()
    section = request.args.get("section", "").strip().upper()
    subject = request.args.get("subject", "").strip()
    attendance_file = "attendance.csv"
    if not os.path.exists(attendance_file):
        return jsonify([])
    df = pd.read_csv(attendance_file).fillna("-")
    for col in ["ID", "Department", "Semester", "Section", "Subject", "Status"]:
        if col not in df.columns:
            df[col] = "-"
    df["Department"] = df["Department"].astype(str).str.strip().str.upper()
    df["Semester"] = df["Semester"].astype(str).str.replace(".0", "", regex=False).str.strip()
    df["Section"] = df["Section"].astype(str).str.strip().str.upper()
    df["Subject"] = df["Subject"].astype(str).str.strip()
    df["ID"] = df["ID"].astype(str).str.strip()
    df = df[
        (df["Department"] == department) &
        (df["Semester"] == semester) &
        (df["Section"] == section) &
        (df["Subject"] == subject)
    ]
    result = []
    for student_id, group in df.groupby("ID"):
        present_count = len(group[group["Status"].astype(str).str.lower() == "present"])
        absent_count = len(group[group["Status"].astype(str).str.lower() == "absent"])
        percentage = 100 + (present_count * 1) - (absent_count * 3)

        if percentage > 100:
            percentage = 100

        if percentage < 0:
            percentage = 0
        result.append({
            "ID": student_id,
            "Percentage": percentage
        })
    return jsonify(result)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
