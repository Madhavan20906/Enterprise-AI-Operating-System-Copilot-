from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.config import settings
from app.infrastructure.database import engine, Base, SessionLocal
from app.db.models import User, RoleEnum
from app.core.security import get_password_hash

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables if they do not exist
    Base.metadata.create_all(bind=engine)
    
    # Initialize a default admin and default employee user if not exist
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@enterprise.com").first()
        if not admin:
            admin_user = User(
                email="admin@enterprise.com",
                hashed_password=get_password_hash("AdminPassword123!"),
                full_name="System Administrator",
                role=RoleEnum.administrator,
                is_active=True
            )
            db.add(admin_user)
            
        employee = db.query(User).filter(User.email == "employee@enterprise.com").first()
        if not employee:
            emp_user = User(
                email="employee@enterprise.com",
                hashed_password=get_password_hash("EmployeePassword123!"),
                full_name="Corporate Employee",
                role=RoleEnum.employee,
                is_active=True
            )
            db.add(emp_user)
            
        db.commit()
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()
        
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

from app.api.main import api_router

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "message": "Welcome to the Enterprise AI Operating System API",
        "version": settings.VERSION,
        "status": "healthy"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
