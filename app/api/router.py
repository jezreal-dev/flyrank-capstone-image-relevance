"""Central API router aggregating modular feature routes."""
from fastapi import APIRouter
from app.api.routes_images import router as images_router
from app.api.routes_posts import router as posts_router
from app.api.routes_reviews import router as reviews_router
from app.api.routes_costs import router as costs_router
from app.api.routes_eval import router as eval_router

api_router = APIRouter()
api_router.include_router(images_router)
api_router.include_router(posts_router)
api_router.include_router(reviews_router)
api_router.include_router(costs_router)
api_router.include_router(eval_router)
