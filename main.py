import os
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from schemas import ProfileUpdate, StudentCreate, CourseCreate, ScheduleCreate
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from fastapi.responses import FileResponse
from fastapi import Depends
from sqlalchemy.orm import Session
from email.mime.text import MIMEText
import database
import models
import csv
import smtplib
# Set up database tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# Disable browser caching so HTML pages are always fresh
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)
# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# Make sure we have a default admin user
def startup_db_check():
    db = database.SessionLocal()
    try:
        admin_user = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin_user:
            new_user = models.User(username="admin", hashed_password="1234") # plain for now
            db.add(new_user)
            db.commit()

        # Seed default courses if database is empty
        course_count = db.query(models.Course).count()
        if course_count == 0:
            default_courses = [
                models.Course(code="CS-101", name="Computer Science", instructor="Dr. Angela Yu", department="Computer Science"),
                models.Course(code="DS-201", name="Data Science", instructor="Dr. Andrew Ng", department="Data Science"),
                models.Course(code="MA-301", name="Mathematics", instructor="Prof. Gilbert Strang", department="Mathematics"),
                models.Course(code="PH-101", name="Physics", instructor="Dr. Richard Feynman", department="Physics"),
                models.Course(code="AI-401", name="AI & ML", instructor="Dr. Yann LeCun", department="Computer Science"),
            ]
            db.add_all(default_courses)
            db.commit()

        # Seed default students if database is empty
        student_count = db.query(models.Student).count()
        if student_count == 0:
            default_students = [
                models.Student(name="Arjun Patel", email="arjun@email.com", course="Computer Science", status="Active", grade="A+"),
                models.Student(name="Sara Khan", email="sara@email.com", course="Data Science", status="Active", grade="A"),
                models.Student(name="Rahul Joshi", email="rahul@email.com", course="Mathematics", status="Pending", grade="B+"),
                models.Student(name="Maya Reddy", email="maya@email.com", course="Physics", status="Active", grade="A-"),
                models.Student(name="Vikram Nair", email="vikram@email.com", course="AI & ML", status="Inactive", grade="B"),
            ]
            db.add_all(default_students)
            db.commit()

        # Seed default schedules if database is empty
        schedule_count = db.query(models.Schedule).count()
        if schedule_count == 0:
            default_schedules = [
                models.Schedule(course_name="Computer Science", instructor="Dr. Angela Yu", day_of_week="Monday", start_time="09:00 AM", end_time="10:30 AM", room="Room 101"),
                models.Schedule(course_name="Data Science", instructor="Dr. Andrew Ng", day_of_week="Tuesday", start_time="11:00 AM", end_time="12:30 PM", room="Room 202"),
                models.Schedule(course_name="Mathematics", instructor="Prof. Gilbert Strang", day_of_week="Wednesday", start_time="02:00 PM", end_time="03:30 PM", room="Lab A"),
                models.Schedule(course_name="Physics", instructor="Dr. Richard Feynman", day_of_week="Thursday", start_time="10:00 AM", end_time="11:30 AM", room="Room 303"),
                models.Schedule(course_name="AI & ML", instructor="Dr. Yann LeCun", day_of_week="Friday", start_time="04:00 PM", end_time="05:30 PM", room="Auditorium"),
            ]
            db.add_all(default_schedules)
            db.commit()
    except Exception as e:
        print(f"Error checking startup data: {e}")
    finally:
        db.close()

startup_db_check()

# Static files
base_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": None}
    )


@app.post("/login")
async def login(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()
    
    if user and user.hashed_password == password:
        return RedirectResponse(url=f"/dashboard?user={username}", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid username or password. Please try again."}
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: str = "admin", db: Session = Depends(database.get_db)):
    students = db.query(models.Student).all()
    
    # Calculate stats
    total_students = len(students)
    active_courses = len(set(s.course for s in students))
    
    passing_grades = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"}
    passing_students = sum(1 for s in students if s.grade in passing_grades)
    pass_rate_pct = int((passing_students / total_students * 100)) if total_students > 0 else 89
    
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "username": user,
            "students": students,
            "total_students": total_students,
            "active_courses": active_courses,
            "pass_rate": f"{pass_rate_pct}%"
        }
    )


@app.get("/profile")
async def profile(
    request: Request,
    user: str = "admin",
    db: Session = Depends(database.get_db)
):
    user_data = db.query(models.User).filter(
        models.User.username == user
    ).first()

    # Check if request comes from browser (expects HTML) or Postman/API client (expects JSON)
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        total_students = db.query(models.Student).count()
        return templates.TemplateResponse(
            request,
            "profile.html",
            {
                "username": user,
                "user": user_data,
                "total_students": total_students
            }
        )
        
    if not user_data:
        return {"message": "User not found"}

    return {
        "username": user_data.username,
        "email": user_data.email,
        "phone": user_data.phone,
        "location": user_data.location,
        "bio": user_data.bio
    }

@app.post("/save-profile")
async def save_profile(
    request: Request,
    original_username: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    location: str = Form(...),
    bio: str = Form(...),
    db: Session = Depends(database.get_db)
):
    try:
        profile_data = ProfileUpdate(
            username=username,
            email=email,
            phone=phone,
            location=location,
            bio=bio
        )
    except ValidationError as e:
        error_msgs = []
        for err in e.errors():
            loc = err.get("loc", ["Unknown"])[0]
            msg = err.get("msg", "")
            if loc == "phone" and "pattern" in err.get("type", ""):
                error_msgs.append("The phone number is not valid.")
            else:
                error_msgs.append(f"{str(loc).capitalize()}: {msg}")
        
        error_text = " | ".join(error_msgs)
        user_data = db.query(models.User).filter(models.User.username == original_username).first()
        return templates.TemplateResponse(
            request,
            "profile.html",
            {
                "username": username,
                "user": user_data,
                "error": error_text
            }
        )
    except Exception as e:
        # Catch-all for other errors
        user_data = db.query(models.User).filter(models.User.username == original_username).first()
        return templates.TemplateResponse(
            request,
            "profile.html",
            {
                "username": username,
                "user": user_data,
                "error": "An error occurred while saving: " + str(e)
            }
        )

    user = db.query(models.User).filter(models.User.username == original_username).first()
    
    # Check if new username is already taken
    if profile_data.username != original_username:
        existing_user = db.query(models.User).filter(models.User.username == profile_data.username).first()
        if existing_user:
            return templates.TemplateResponse(
                request,
                "profile.html",
                {
                    "username": original_username,
                    "user": user,
                    "error": "Username is already taken. Please choose another."
                }
            )

    if user:
        user.username = profile_data.username
        user.email = profile_data.email
        user.phone = profile_data.phone
        user.location = profile_data.location
        user.bio = profile_data.bio
    else:
        user = models.User(
            username=profile_data.username,
            email=profile_data.email,
            phone=profile_data.phone,
            location=profile_data.location,
            bio=profile_data.bio,
            hashed_password="1234"
        )
        db.add(user)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            request,
            "profile.html",
            {
                "username": original_username,
                "user": user,
                "error": "Database error occurred while saving."
            }
        )

    return RedirectResponse(url=f"/profile?user={profile_data.username}", status_code=303)

@app.get("/api/admin")
async def admin_api(user: str = "admin"):
    return {
        "username": user,
        "role": "admin",
        "status": "active"
    }
@app.put("/users/{user_id}")
def update_user(user_id: int, user_data: ProfileUpdate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        return {"message": "User not found"}

    user.username = user_data.username
    user.email = user_data.email
    user.phone = user_data.phone
    user.location = user_data.location
    user.bio = user_data.bio

    db.commit()
    db.refresh(user)

    return {"message": "User updated successfully"}
@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        return {"message": "User not found"}

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}
@app.post("/change-password")
async def change_password(
    request: Request,
    username: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(
        models.User.username == username
    ).first()

    if not user:
        return templates.TemplateResponse(request, "profile.html", {"username": username, "user": None, "error": "User not found"})

    if user.hashed_password != current_password:
        return templates.TemplateResponse(request, "profile.html", {"username": username, "user": user, "error": "Current password is incorrect"})

    user.hashed_password = new_password
    db.commit()

    return RedirectResponse(
        url=f"/profile?user={username}&pwd_changed=1",
        status_code=303
    )

@app.post("/students/add")
async def add_student(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    course: str = Form(...),
    status: str = Form("Active"),
    grade: str = Form(""),
    db: Session = Depends(database.get_db)
):
    try:
        student_data = StudentCreate(
            name=name,
            email=email,
            course=course,
            status=status,
            grade=grade
        )
    except ValidationError as e:
        error_msgs = []
        for err in e.errors():
            loc = err.get("loc", ["Unknown"])[0]
            msg = err.get("msg", "")
            error_msgs.append(f"{str(loc).capitalize()}: {msg}")
        return {"success": False, "message": " | ".join(error_msgs)}
    
    # Check for duplicate email
    existing_student = db.query(models.Student).filter(models.Student.email == student_data.email).first()
    if existing_student:
        return {"success": False, "message": "A student with this email address already exists."}
    
    new_student = models.Student(
        name=student_data.name,
        email=student_data.email,
        course=student_data.course,
        status=student_data.status,
        grade=student_data.grade
    )
    
    try:
        db.add(new_student)
        db.commit()
        return {"success": True, "message": "Student added successfully."}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}

@app.get("/students", response_class=HTMLResponse)
async def students_page(request: Request, user: str = "admin", db: Session = Depends(database.get_db)):
    students = db.query(models.Student).all()
    courses = db.query(models.Course).all()
    return templates.TemplateResponse(
        request,
        "students.html",
        {
            "username": user,
            "students": students,
            "courses": courses,
            "total_students": len(students)
        }
    )

@app.post("/students/edit/{student_id}")
async def edit_student(
    student_id: int,
    name: str = Form(...),
    email: str = Form(...),
    course: str = Form(...),
    status: str = Form(...),
    grade: str = Form(""),
    db: Session = Depends(database.get_db)
):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        return {"success": False, "message": "Student not found."}
    
    try:
        student_data = StudentCreate(
            name=name,
            email=email,
            course=course,
            status=status,
            grade=grade
        )
    except ValidationError as e:
        error_msgs = []
        for err in e.errors():
            loc = err.get("loc", ["Unknown"])[0]
            msg = err.get("msg", "")
            error_msgs.append(f"{str(loc).capitalize()}: {msg}")
        return {"success": False, "message": " | ".join(error_msgs)}
    
    # Check duplicate email (excluding self)
    dup = db.query(models.Student).filter(models.Student.email == email, models.Student.id != student_id).first()
    if dup:
        return {"success": False, "message": "A student with this email address already exists."}
    
    student.name = student_data.name
    student.email = student_data.email
    student.course = student_data.course
    student.status = student_data.status
    student.grade = student_data.grade
    
    try:
        db.commit()
        return {"success": True, "message": "Student updated successfully."}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}

@app.post("/students/delete/{student_id}")
async def delete_student(student_id: int, db: Session = Depends(database.get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        return {"success": False, "message": "Student not found."}
    try:
        db.delete(student)
        db.commit()
        return {"success": True, "message": "Student deleted successfully."}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}

@app.get("/courses", response_class=HTMLResponse)
async def courses_page(request: Request, user: str = "admin", db: Session = Depends(database.get_db)):
    courses = db.query(models.Course).all()
    students = db.query(models.Student).all()
    
    course_counts = {}
    for student in students:
        course_counts[student.course] = course_counts.get(student.course, 0) + 1
    
    courses_data = []
    for c in courses:
        courses_data.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "instructor": c.instructor or "TBD",
            "department": c.department or "TBD",
            "students_count": course_counts.get(c.name, 0)
        })
    
    return templates.TemplateResponse(
        request,
        "courses.html",
        {
            "username": user,
            "courses": courses_data,
            "total_students": len(students)
        }
    )

@app.post("/courses/add")
async def add_course(
    code: str = Form(...),
    name: str = Form(...),
    instructor: str = Form(""),
    department: str = Form(""),
    db: Session = Depends(database.get_db)
):
    try:
        course_data = CourseCreate(
            code=code,
            name=name,
            instructor=instructor,
            department=department
        )
    except ValidationError as e:
        error_msgs = []
        for err in e.errors():
            loc = err.get("loc", ["Unknown"])[0]
            msg = err.get("msg", "")
            error_msgs.append(f"{str(loc).capitalize()}: {msg}")
        return {"success": False, "message": " | ".join(error_msgs)}
    
    dup_code = db.query(models.Course).filter(models.Course.code == course_data.code).first()
    if dup_code:
        return {"success": False, "message": "A course with this code already exists."}
    
    dup_name = db.query(models.Course).filter(models.Course.name == course_data.name).first()
    if dup_name:
        return {"success": False, "message": "A course with this name already exists."}
    
    new_course = models.Course(
        code=course_data.code,
        name=course_data.name,
        instructor=course_data.instructor,
        department=course_data.department
    )
    try:
        db.add(new_course)
        db.commit()
        return {"success": True, "message": "Course added successfully."}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}

@app.post("/courses/edit/{course_id}")
async def edit_course(
    course_id: int,
    code: str = Form(...),
    name: str = Form(...),
    instructor: str = Form(""),
    department: str = Form(""),
    db: Session = Depends(database.get_db)
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        return {"success": False, "message": "Course not found."}
    
    try:
        course_data = CourseCreate(
            code=code,
            name=name,
            instructor=instructor,
            department=department
        )
    except ValidationError as e:
        error_msgs = []
        for err in e.errors():
            loc = err.get("loc", ["Unknown"])[0]
            msg = err.get("msg", "")
            error_msgs.append(f"{str(loc).capitalize()}: {msg}")
        return {"success": False, "message": " | ".join(error_msgs)}
    
    dup_code = db.query(models.Course).filter(models.Course.code == code, models.Course.id != course_id).first()
    if dup_code:
        return {"success": False, "message": "Another course has this code."}
    
    dup_name = db.query(models.Course).filter(models.Course.name == name, models.Course.id != course_id).first()
    if dup_name:
        return {"success": False, "message": "Another course has this name."}
    
    # Update students who have the old course name
    old_name = course.name
    if old_name != course_data.name:
        db.query(models.Student).filter(models.Student.course == old_name).update({models.Student.course: course_data.name})
    
    course.code = course_data.code
    course.name = course_data.name
    course.instructor = course_data.instructor
    course.department = course_data.department
    
    try:
        db.commit()
        return {"success": True, "message": "Course updated successfully."}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}

@app.post("/courses/delete/{course_id}")
async def delete_course(course_id: int, db: Session = Depends(database.get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        return {"success": False, "message": "Course not found."}
    
    try:
        db.delete(course)
        db.commit()
        return {"success": True, "message": "Course deleted successfully."}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}

@app.get("/grades", response_class=HTMLResponse)
async def grades_page(request: Request, user: str = "admin", db: Session = Depends(database.get_db)):
    students = db.query(models.Student).all()
    
    distribution = {"A": 0, "B": 0, "C": 0, "D_F": 0, "None": 0}
    passing_grades = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"}
    passing_count = 0
    graded_count = 0
    
    for s in students:
        g = s.grade
        if not g:
            distribution["None"] += 1
        else:
            graded_count += 1
            if g in passing_grades:
                passing_count += 1
            
            g_upper = g.upper()
            if g_upper.startswith("A"):
                distribution["A"] += 1
            elif g_upper.startswith("B"):
                distribution["B"] += 1
            elif g_upper.startswith("C"):
                distribution["C"] += 1
            else:
                distribution["D_F"] += 1
                
    pass_rate = int((passing_count / graded_count * 100)) if graded_count > 0 else 100
    
    return templates.TemplateResponse(
        request,
        "grades.html",
        {
            "username": user,
            "students": students,
            "distribution": distribution,
            "pass_rate": f"{pass_rate}%",
            "graded_count": graded_count,
            "total_students": len(students)
        }
    )

@app.post("/grades/update")
async def update_grade(
    student_id: int = Form(...),
    grade: str = Form(...),
    db: Session = Depends(database.get_db)
):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        return {"success": False, "message": "Student not found."}
    
    student.grade = grade
    try:
        db.commit()
        return {"success": True, "message": "Grade updated successfully."}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: str = "admin", db: Session = Depends(database.get_db)):
    total_students = db.query(models.Student).count()
    total_courses = db.query(models.Course).count()
    total_users = db.query(models.User).count()
    db_engine_name = db.bind.name if db.bind else "SQLite"
    
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "username": user,
            "total_students": total_students,
            "total_courses": total_courses,
            "total_users": total_users,
            "db_type": db_engine_name.upper()
        }
    )

@app.post("/settings/reset-db")
async def reset_db(db: Session = Depends(database.get_db)):
    try:
        db.query(models.Student).delete()
        db.query(models.Course).delete()
        db.query(models.User).delete()
        db.query(models.Schedule).delete()
        db.commit()
        
        admin_user = models.User(username="admin", hashed_password="1234")
        db.add(admin_user)
        
        default_courses = [
            models.Course(code="CS-101", name="Computer Science", instructor="Dr. Angela Yu", department="Computer Science"),
            models.Course(code="DS-201", name="Data Science", instructor="Dr. Andrew Ng", department="Data Science"),
            models.Course(code="MA-301", name="Mathematics", instructor="Prof. Gilbert Strang", department="Mathematics"),
            models.Course(code="PH-101", name="Physics", instructor="Dr. Richard Feynman", department="Physics"),
            models.Course(code="AI-401", name="AI & ML", instructor="Dr. Yann LeCun", department="Computer Science"),
        ]
        db.add_all(default_courses)
        
        default_students = [
            models.Student(name="Arjun Patel", email="arjun@email.com", course="Computer Science", status="Active", grade="A+"),
            models.Student(name="Sara Khan", email="sara@email.com", course="Data Science", status="Active", grade="A"),
            models.Student(name="Rahul Joshi", email="rahul@email.com", course="Mathematics", status="Pending", grade="B+"),
            models.Student(name="Maya Reddy", email="maya@email.com", course="Physics", status="Active", grade="A-"),
            models.Student(name="Vikram Nair", email="vikram@email.com", course="AI & ML", status="Inactive", grade="B"),
        ]
        db.add_all(default_students)

        default_schedules = [
            models.Schedule(course_name="Computer Science", instructor="Dr. Angela Yu", day_of_week="Monday", start_time="09:00 AM", end_time="10:30 AM", room="Room 101"),
            models.Schedule(course_name="Data Science", instructor="Dr. Andrew Ng", day_of_week="Tuesday", start_time="11:00 AM", end_time="12:30 PM", room="Room 202"),
            models.Schedule(course_name="Mathematics", instructor="Prof. Gilbert Strang", day_of_week="Wednesday", start_time="02:00 PM", end_time="03:30 PM", room="Lab A"),
            models.Schedule(course_name="Physics", instructor="Dr. Richard Feynman", day_of_week="Thursday", start_time="10:00 AM", end_time="11:30 AM", room="Room 303"),
            models.Schedule(course_name="AI & ML", instructor="Dr. Yann LeCun", day_of_week="Friday", start_time="04:00 PM", end_time="05:30 PM", room="Auditorium"),
        ]
        db.add_all(default_schedules)
        
        db.commit()
        return {"success": True, "message": "Database reset to factory defaults successfully!"}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Reset failed: {str(e)}"}

@app.get("/schedule", response_class=HTMLResponse)
async def schedule_page(request: Request, user: str = "admin", db: Session = Depends(database.get_db)):
    schedules = db.query(models.Schedule).all()
    courses = db.query(models.Course).all()
    total_students = db.query(models.Student).count()
    return templates.TemplateResponse(
        request,
        "schedule.html",
        {
            "username": user,
            "schedules": schedules,
            "courses": courses,
            "total_students": total_students
        }
    )

@app.post("/schedule/add")
async def add_schedule(
    course_name: str = Form(...),
    instructor: str = Form(""),
    day_of_week: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    room: str = Form(""),
    db: Session = Depends(database.get_db)
):
    try:
        sched_data = ScheduleCreate(
            course_name=course_name,
            instructor=instructor,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            room=room
        )
    except ValidationError as e:
        error_msgs = []
        for err in e.errors():
            loc = err.get("loc", ["Unknown"])[0]
            msg = err.get("msg", "")
            error_msgs.append(f"{str(loc).capitalize()}: {msg}")
        return {"success": False, "message": " | ".join(error_msgs)}
    
    new_sched = models.Schedule(
        course_name=sched_data.course_name,
        instructor=sched_data.instructor,
        day_of_week=sched_data.day_of_week,
        start_time=sched_data.start_time,
        end_time=sched_data.end_time,
        room=sched_data.room
    )
    try:
        db.add(new_sched)
        db.commit()
        return {"success": True, "message": "Schedule entry added successfully."}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}

@app.post("/schedule/delete/{schedule_id}")
async def delete_schedule(schedule_id: int, db: Session = Depends(database.get_db)):
    sched = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not sched:
        return {"success": False, "message": "Schedule entry not found."}
    try:
        db.delete(sched)
        db.commit()
        return {"success": True, "message": "Schedule entry deleted successfully."}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}
@app.get("/export-students")
async def export_students(db: Session = Depends(database.get_db)):

    students = db.query(models.Student).all()

    filename = "students_export.csv"

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "ID",
            "Name",
            "Email",
            "Course",
            "Status",
            "Grade"
        ])

        for student in students:
            writer.writerow([
                student.id,
                student.name,
                student.email,
                student.course,
                student.status,
                student.grade
            ])

    return FileResponse(
        path=filename,
        filename=filename,
        media_type="text/csv"
    ) 
@app.get("/send-email")
async def send_email(db: Session = Depends(database.get_db)):

    students = db.query(models.Student).all()

    body = "Student List\n\n"

    for s in students:
        body += f"""
Name: {s.name}
Email: {s.email}
Course: {s.course}
Status: {s.status}
Grade: {s.grade}

"""

    msg = MIMEText(body)
    msg["Subject"] = "Student Report"
    msg["From"] = "simhadrijamisetti@gmail.com"
    msg["To"] = "admin@gmail.com"

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()

    server.login(
        "simhadrijamisetti@gmail.com",
        "tbzm gjwg jgov fjoi"
    )

    server.send_message(msg)
    server.quit()

    return RedirectResponse(
        url="/dashboard?email_sent=1",
        status_code=303
    )