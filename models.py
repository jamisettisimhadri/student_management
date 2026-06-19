from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), unique=True, index=True)

    hashed_password = Column(String(100))

    email = Column(String(100))

    phone = Column(String(20))

    location = Column(String(100))

    bio = Column(String(300))

    is_active = Column(Boolean, default=True)

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    course = Column(String(100), nullable=False)
    status = Column(String(20), default="Active")
    grade = Column(String(10), nullable=True)

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), unique=True, index=True, nullable=False)
    instructor = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    course_name = Column(String(100), nullable=False)
    instructor = Column(String(100), nullable=True)
    day_of_week = Column(String(20), nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    room = Column(String(50), nullable=True)