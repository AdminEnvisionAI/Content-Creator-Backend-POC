from fastapi import FastAPI
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document
from models.influencer import InfluencerProfile
from routes.influencer import router
import os, importlib, pkgutil
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="Influencer Rank API")
# CORS Middleware
origins = [
    "https://teachologyai.com",
    "http://teachologyai.com",
    "https://www.teachologyai.com",
    "http://www.teachologyai.com",
    "http://stage.teachologyai.com",
    "https://stage.teachologyai.com",
    "http://localhost:5173",
    "http://localhost:5174",
    "https://aistudio.google.com"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_NAME = os.getenv("MONGODB_NAME")


async def load_beanie_models():
    """
    Dynamically load all Beanie Document models from db_schemas folder.
    """
    import models
    model_classes = []

    for _, module_name, _ in pkgutil.iter_modules(models.__path__):
        module = importlib.import_module(f"models.{module_name}")
        for attr in dir(module):
            value = getattr(module, attr)
            try:
                if isinstance(value, type) and issubclass(value, Document) and value is not Document:
                    model_classes.append(value)
            except TypeError:
                pass

    return model_classes


@app.on_event("startup")
async def startup_event():
    """
    Initialize MongoDB + Beanie at startup.
    """
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[MONGODB_NAME]
        print("✅ MongoDB Connected!")

        # Load dynamic Beanie Models OR fallback to InfluencerModel
        try:
            models = await load_beanie_models()
            if not models:
                models = [InfluencerProfile]
        except:
            models = [InfluencerProfile]

        await init_beanie(database=db, document_models=models)

        print("✅ Beanie Initialized with Models:", [model.__name__ for model in models])

    except Exception as e:
        print("❌ MongoDB Initialization Failed:", e)


# Include API Routes
app.include_router(router, prefix="/api/v1", tags=["influencers"])
