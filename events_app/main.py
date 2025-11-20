from fastapi import FastAPI
from .database import engine, Base 
from .api_router import router
from . import models 
import logging

Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Events Microservice",
    description="Microservice for managing events and scheduling",
    version="1.0.0"
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "service": "Events",
        "status": "running"
    }