from fastapi import FastAPI
from routers.users import router as user_router, root_router
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {'message': 'Hello World'}

@app.get("/predict")
async def predict(
    seller_id: int,
    is_verified_seller: bool,
    item_id: int,
    name: str,
    description: str,
    category: int,
    images_qty: Optional[int, None]
) -> bool:
    if is_verified_seller:
        return True
    if images_qty is not None:
        return True
    return False


app.include_router(user_router, prefix='/users')
app.include_router(root_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)