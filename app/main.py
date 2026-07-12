from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import home_page_routes, user_routes, new_arrivals_routes
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="ManMohhey API",
    version="1.0.0",
    description="API for ManMohhey application",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/public", StaticFiles(directory="public"), name="public")
app.include_router(home_page_routes.router)
app.include_router(user_routes.router)
app.include_router(new_arrivals_routes.router)