from pydantic import BaseModel, EmailStr, Field

class ProfileUpdate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    phone: str = Field(default="")
    location: str = Field(default="")
    bio: str = Field(default="")

class StudentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    course: str = Field(..., min_length=2, max_length=100)
    status: str = Field(default="Active")
    grade: str = Field(default="")

class CourseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    instructor: str = Field(default="", max_length=100)
    department: str = Field(default="", max_length=100)

class ScheduleCreate(BaseModel):
    course_name: str = Field(..., min_length=2, max_length=100)
    instructor: str = Field(default="", max_length=100)
    day_of_week: str = Field(..., min_length=3, max_length=20)
    start_time: str = Field(..., min_length=4, max_length=10)
    end_time: str = Field(..., min_length=4, max_length=10)
    room: str = Field(default="", max_length=50)