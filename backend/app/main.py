from fastapi import FastAPI

app = FastAPI(title="Parley")


@app.get("/health")
def health():
    return {"status": "ok"}
