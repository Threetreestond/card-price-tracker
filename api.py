import sys
sys.path.insert(0, "src")
from fastapi import FastAPI
from database import get_all_decks

app = FastAPI()

@app.get("/")
def root():
    return {"message": "hello"}

@app.get("/decks")
def get_decks():
    return get_all_decks()