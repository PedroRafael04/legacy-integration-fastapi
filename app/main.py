from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import transformation, health

app = FastAPI(
    title="Legacy System Integration API",
    description="Data transformation layer bridging legacy systems with modern applications.",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(health.router, tags=["Health"])
app.include_router(transformation.router, prefix="/api/v1", tags=["Transformation"])

@app.get("/", tags=["Root"])
def root():
    return {
        "service": "Legacy System Integration API",
        "version": "1.0.0",
        "docs": "/docs",
    }
