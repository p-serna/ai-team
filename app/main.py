from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aio_pika
from typing import Optional
import uuid
import json

app = FastAPI()

class CodeRequest(BaseModel):
    prompt: str
    language: Optional[str] = "python"
    max_tokens: Optional[int] = 2000

class CodeResponse(BaseModel):
    request_id: str
    status: str = "pending"

async def connect_rabbitmq():
    connection = await aio_pika.connect_robust(
        "amqp://rabbitmq:5672"
    )
    channel = await connection.channel()
    await channel.declare_queue("code_requests", durable=True)
    return connection, channel

@app.on_event("startup")
async def startup():
    app.rabbitmq_connection, app.rabbitmq_channel = await connect_rabbitmq()

@app.on_event("shutdown")
async def shutdown():
    await app.rabbitmq_connection.close()

@app.post("/generate-code", response_model=CodeResponse)
async def generate_code(request: CodeRequest):
    request_id = str(uuid.uuid4())
    
    message = aio_pika.Message(
        body=json.dumps({
            "request_id": request_id,
            "prompt": request.prompt,
            "language": request.language,
            "max_tokens": request.max_tokens
        }).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
    )
    
    await app.rabbitmq_channel.default_exchange.publish(
        message,
        routing_key="code_requests"
    )
    
    return CodeResponse(request_id=request_id)

@app.get("/status/{request_id}")
async def get_status(request_id: str):
    # In a real implementation, you would check a database for the status
    # This is a simplified version
    return {"status": "pending"}