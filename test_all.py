from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=True)

def test_routes():
    print("GET /login", client.get("/").status_code)
    
    print("POST /login", client.post("/login", data={"username": "admin", "password": "wrong"}).status_code)
    print("POST /login (correct)", client.post("/login", data={"username": "admin", "password": "1234"}).status_code)

    print("GET /dashboard", client.get("/dashboard?user=admin").status_code)
    
    res = client.get("/profile?user=admin")
    print("GET /profile?user=admin", res.status_code)
    if res.status_code >= 500:
        print("ERROR BODY:", res.text)
        
    res2 = client.post("/save-profile", data={
        "username": "admin2",
        "email": "test@test.com",
        "phone": "123",
        "location": "test",
        "bio": "test"
    })
    print("POST /save-profile", res2.status_code)
    if res2.status_code >= 500:
        print("ERROR BODY:", res2.text)

    # Test /students/add endpoint
    print("\n--- Testing Student Insertion ---")
    
    # 1. Add student with invalid email
    res_invalid_email = client.post("/students/add", data={
        "name": "Invalid Student",
        "email": "not-an-email",
        "course": "Math",
        "status": "Active",
        "grade": "A"
    })
    print("POST /students/add (invalid email):", res_invalid_email.status_code, res_invalid_email.json())

    # 2. Add valid student
    import random
    rand_email = f"student.{random.randint(1000, 9999)}@example.com"
    res_valid = client.post("/students/add", data={
        "name": "Jane Doe",
        "email": rand_email,
        "course": "Chemistry",
        "status": "Active",
        "grade": "A+"
    })
    print("POST /students/add (valid student):", res_valid.status_code, res_valid.json())

    # 3. Add duplicate student email
    res_dup = client.post("/students/add", data={
        "name": "Jane Doe Duplicate",
        "email": rand_email,
        "course": "Chemistry",
        "status": "Active",
        "grade": "A+"
    })
    print("POST /students/add (duplicate student):", res_dup.status_code, res_dup.json())

    # 4. GET /students
    res_students = client.get("/students?user=admin")
    print("GET /students:", res_students.status_code)
    
    # 5. GET /courses
    res_courses = client.get("/courses?user=admin")
    print("GET /courses:", res_courses.status_code)

    # 6. POST /courses/add
    rand_code = f"CS-{random.randint(100, 999)}"
    res_add_course = client.post("/courses/add", data={
        "code": rand_code,
        "name": f"Intro to Coding {rand_code}",
        "instructor": "Dr. Angela Yu",
        "department": "Computer Science"
    })
    print("POST /courses/add:", res_add_course.status_code, res_add_course.json())

    # 7. GET /grades
    res_grades = client.get("/grades?user=admin")
    print("GET /grades:", res_grades.status_code)

    # 8. GET /settings
    res_settings = client.get("/settings?user=admin")
    print("GET /settings:", res_settings.status_code)

    # 9. GET /schedule
    res_schedule = client.get("/schedule?user=admin")
    print("GET /schedule:", res_schedule.status_code)

    # 10. POST /schedule/add
    res_add_schedule = client.post("/schedule/add", data={
        "course_name": "Computer Science",
        "instructor": "Dr. Angela Yu",
        "day_of_week": "Monday",
        "start_time": "10:30 AM",
        "end_time": "12:00 PM",
        "room": "Room 105"
    })
    print("POST /schedule/add:", res_add_schedule.status_code, res_add_schedule.json())

test_routes()
