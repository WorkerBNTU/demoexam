from typing import Annotated

from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy.exc import IntegrityError


app = FastAPI()
app.mount("/static", StaticFiles(directory="./static"))
templates = Jinja2Templates("templates")

class Record(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    course: str
    date: str
    payment: str
    status: str
    user_id: int

class NewRecord(SQLModel):
    course: str
    date: str
    payment: str

class User(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    login: str = Field(unique=True, min_length=6)
    password: str = Field(min_length=8)
    email: str
    fio: str
    phone: str
    role: str | None = Field(default="user")

class UserAuth(SQLModel):
    login: str
    password: str


DATABASE_URL = "postgresql://postgres:123@localhost:5432/demoexam"
engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(bind=engine)

@app.get("/")
def index(request: Request):
    role = request.cookies.get("role")

    if not role:
        return RedirectResponse("/login", status_code=302)

    if role == "admin":
        return RedirectResponse("/admin", status_code=302)

    return RedirectResponse("/profile", status_code=302)

@app.get("/login")
def login_page(request: Request):

    if request.cookies.get("role"):
        return RedirectResponse("/", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

@app.post("/login")
def login_process(request: Request, data: Annotated[UserAuth, Form()]):
    response = RedirectResponse("/", status_code=302)
    if data.login == "Admin" and data.password == "KorokNET":
        response.set_cookie("role", "admin")
        return response

    with Session(bind=engine) as session:
        s = select(User).where(User.login == data.login).where(User.password == data.password)
        user = session.exec(s).one_or_none()
        # user или хранит объект класса User, либо None
        if not user:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={
                    "error": "Данный пользователь не найден"
                }
            )

        response.set_cookie("role", user.role)
        response.set_cookie("user_id", user.id)
        return response


@app.get("/register")
def register_page(request: Request):
    if request.cookies.get("role"):
        return RedirectResponse("/", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )

@app.post("/register")
def register_page(request: Request, data: Annotated[User, Form()]):
    with Session(bind=engine) as session:
        try:
            session.add(data)
            session.commit()
        except IntegrityError:
            session.rollback()
            return templates.TemplateResponse(
                request=request,
                name="register.html",
                context={
                    "error": "Логин уже занят"
                }
            )

    return RedirectResponse("/login", status_code=302)


@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("role")
    response.delete_cookie("user_id")
    return response

@app.get("/profile")
def profile(request: Request):
    if request.cookies.get("role") != "user":
        return RedirectResponse("/", 302)

    user_id = request.cookies.get("user_id")

    with Session(bind=engine) as session:
        s = select(Record).where(Record.user_id == user_id)
        records = session.exec(s).all()

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "records": records
        }
    )

@app.get("/create")
def create_page(request: Request):
    if not request.cookies.get("role"):
        return RedirectResponse("/", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="create.html"
    )

@app.post("/create")
def create_record(request: Request, data: Annotated[NewRecord, Form()]):
    user_id = request.cookies.get("user_id")

    with Session(bind=engine) as session:
        session.add(Record(
            course=data.course,
            date=data.date,
            payment=data.payment,
            status="Новая",
            user_id=user_id
        ))
        session.commit()

    return RedirectResponse("/profile", status_code=302)


@app.get("/admin")
def admin_page(request: Request):
    if request.cookies.get("role") != "admin":
        return RedirectResponse("/", 302)

    with Session(bind=engine) as session:
        s = select(Record, User).where(Record.user_id == User.id)
        records = session.exec(s).all()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "records": records
        }
    )

@app.post("/update/{record_id}")
def update_record(record_id: int, status: Annotated[str, Form()]):
    with Session(bind=engine) as session:
        s = select(Record).where(Record.id == record_id)
        record = session.exec(s).one()
        record.status = status
        session.add(record)
        session.commit()
        session.refresh(record)

    return RedirectResponse("/admin", 302)