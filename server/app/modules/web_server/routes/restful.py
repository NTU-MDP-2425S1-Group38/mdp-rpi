from time import strftime, localtime

from fastapi import APIRouter

rest_endpoints = APIRouter()


@rest_endpoints.get("/")
async def index():
    return f"Hello the time now is {strftime('%Y-%m-%d_%H-%M-%S', localtime())}"
