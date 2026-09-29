from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def record_delivery(delivery_id: str, seen: set[str]) -> bool:
    seen.add(delivery_id)
    return True
