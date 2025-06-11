from fastapi import APIRouter

fake_router = APIRouter()


@fake_router.post("/fake")
def test():
    return {
        "Status": "success"
    }
