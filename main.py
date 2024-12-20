import os
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI
from chunks import Chunk

bot_token = os.getenv("TOKEN_BOT_GPT_MODEL")

app = FastAPI()
chunk_instance = Chunk()


class Item(BaseModel):
    text: str


@app.get("/")
async def read_root():
    return {"message": "Привет, введите ваш вопрос."}


@app.post("/ask")
async def get_answer_async(question: Item):
    answer = await chunk_instance.async_get_answer(question=question.text)
    return {"message": answer}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
