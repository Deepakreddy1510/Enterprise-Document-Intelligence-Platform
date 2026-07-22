from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from app.api.v1.routes import router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Document


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as s:
        await s.execute(
            update(Document)
            .where(Document.status == "processing")
            .values(
                status="failed",
                processing_error="Processing interrupted by backend restart; retry this document.",
            )
        )
        await s.commit()
    yield


app = FastAPI(title="Enterprise RAG Assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")
