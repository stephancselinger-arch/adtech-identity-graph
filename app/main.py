from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import identity, sync, privacy

app = FastAPI(
    title="AdTech Identity Graph",
    description=(
        "Identity resolution and cookieless tracking service. "
        "Stitches cookie IDs, device IDs, email/phone hashes, PPIDs, UID2 tokens, "
        "and probabilistic fingerprints into unified identity profiles using a "
        "Union-Find graph with GDPR/CCPA consent management."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(identity.router, prefix="/v1")
app.include_router(sync.router, prefix="/v1")
app.include_router(privacy.router, prefix="/v1")


@app.get("/health")
def health():
    return {"status": "ok", "service": "adtech-identity-graph"}
