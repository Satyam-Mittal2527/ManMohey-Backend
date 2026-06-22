from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import home_page_routes, user_routes
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="ManMohhey API",
    version="1.0.0",
    description="API for ManMohhey application",
)
@app.middleware("http")
async def log_origin(request, call_next):
    print("METHOD:", request.method)
    print("ORIGIN:", request.headers.get("origin"))
    response = await call_next(request)
    return response
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.1.84:3000",
        "https://manmohey-seven.vercel.app/"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers = ["*"],
)


app.mount("/public", StaticFiles(directory="public"), name="public")
app.include_router(home_page_routes.router)
app.include_router(user_routes.router)