from flask import Flask, render_template, Response
import cv2
import csv
from datetime import datetime, timedelta

app = Flask(__name__)

# Paths to store CSV data
db_file = "db.csv"
log_file = "log.csv"

# Initialize the CSV database
with open(db_file, "w", newline='') as db:
    db_writer = csv.writer(db)
    db_writer.writerow(["Classroom", "Student", "Entry Time", "Status"])

# Dictionary to keep track of active students
active_people = {}
last_student = None  # Initialize last_student to None
classroom = 1214

# Timetable mapping (hours to subjects)
timetable = {8: "OSY", 9: "DBMS", 10: "STE", 12: "EVN", 15: "AJP", 23: "CSS"}

# Function to calculate time difference
def diff(start, end, secs):
    end_time = datetime.strptime(end, '%H:%M:%S')
    start_time = datetime.strptime(start, '%H:%M:%S')
    return abs(end_time - start_time) >= timedelta(seconds=secs)

# Initialize the QR Code detector
qr_decoder = cv2.QRCodeDetector()

# Function to capture frames and detect QR codes
def gen_frames():
    global last_student  # Declare last_student as global
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)

    while True:
        success, frame = cap.read()
        if not success:
            break

        # Detect and decode the QR code from the frame
        data, bbox, _ = qr_decoder.detectAndDecode(frame)

        if data:
            student = data.strip()  # Student ID from QR code
            now = datetime.now().strftime('%H:%M:%S')

            # Check if student is leaving
            if student in active_people.keys():
                student_exit_time = datetime.now().strftime('%H:%M:%S')
                if diff(active_people[student], student_exit_time, 10):
                    print(f"{student} joined at {active_people[student]} and left at {student_exit_time}")
                    
                    # Log student's exit and update the CSV
                    with open(db_file, "r", newline='') as db_read:
                        rows = list(csv.reader(db_read))
                        rows = [row for row in rows if row[1] != student]  # Remove from active list
                    
                    with open(db_file, "w", newline='') as db_write:
                        db_writer = csv.writer(db_write)
                        db_writer.writerows(rows)

                    with open(log_file, "a", newline='') as log:
                        log_writer = csv.writer(log)
                        log_writer.writerow([classroom, student, active_people[student], student_exit_time])

                    active_people.pop(student)
            else:
                # Check if the student is new
                if student != last_student:
                    current_hour = int(now.split(":")[0])
                    if current_hour in timetable.keys():
                        data = [classroom, student, now, "Yes"]
                    else:
                        data = [classroom, student, now, "No"]

                    # Log student's entry into the active database
                    with open(db_file, "a", newline='') as db:
                        db_writer = csv.writer(db)
                        db_writer.writerow(data)

                    last_student = student
                    active_people[student] = now  # Store entry time

        # Encode frame to JPEG format to be streamed
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        # Yield the frame to the client
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

@app.route('/')
def index():
    """Homepage for video streaming."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video feed route."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)
