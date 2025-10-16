from fastapi import FastAPI
import os

app = FastAPI(title="Leonor AI", version="1.0")

@app.get("/")
def read_root():
    return {"message": "🚀 Leonor AI Multi-Provider API"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "Leonor AI",
        "providers": ["huggingface", "openrouter"]
    }

@app.get("/test")
def test_endpoint():
    return {"message": "Sistema funcionando perfeitamente!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
