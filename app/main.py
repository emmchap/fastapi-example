from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def print_hello_world():
    return "Hello World"
