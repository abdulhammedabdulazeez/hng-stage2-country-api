from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db
from app.routes import router


@asynccontextmanager
async def life_span(app: FastAPI):
    print(f"Server is starting ...")
    await init_db()
    yield
    print(f"Server has been stopped ...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=life_span,
)

# Include router
app.include_router(router)
