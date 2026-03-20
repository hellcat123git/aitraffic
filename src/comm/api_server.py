from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class TrafficData(BaseModel):
    road1_count: int
    road2_count: int
    road1_signal: str
    road2_signal: str
    road1_emergency: int
    road2_emergency: int
    total_co2_saved: float

# Global state
current_data = {
    "road1_count": 0,
    "road2_count": 0,
    "road1_signal": "RED",
    "road2_signal": "RED",
    "road1_emergency": 0,
    "road2_emergency": 0,
    "total_co2_saved": 0.0
}

@app.get("/data")
async def get_data():
    return current_data

@app.post("/update")
async def update_data(data: TrafficData):
    global current_data
    current_data = data.dict()
    return {"status": "success"}

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run_server()
