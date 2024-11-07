# agent-service/agent.py
import asyncio
import aio_pika
import httpx
import json
from typing import Dict, Any

class CodeGenerationAgent:
    def __init__(self):
        self.llm_api_url = "http://llm-service:8080/completion"
        self.system_prompt = """You are an expert programmer. Your task is to write clean, 
        efficient, and well-documented code based on the requirements provided. Always include:
        1. Clear documentation
        2. Error handling
        3. Type hints (for Python)
        4. Comments explaining complex logic
        """

    async def connect_rabbitmq(self):
        self.connection = await aio_pika.connect_robust(
            "amqp://rabbitmq:5672"
        )
        self.channel = await self.connection.channel()
        self.queue = await self.channel.declare_queue(
            "code_requests",
            durable=True
        )

    async def generate_code(self, prompt: str, language: str, max_tokens: int) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.llm_api_url,
                json={
                    "prompt": f"{self.system_prompt}\n\nRequirement: {prompt}\nLanguage: {language}",
                    "max_tokens": max_tokens,
                    "temperature": 0.2  # Lower temperature for more focused code generation
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"LLM API error: {response.text}")
            
            return response.json()["completion"]

    async def process_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                code = await self.generate_code(
                    prompt=body["prompt"],
                    language=body["language"],
                    max_tokens=body["max_tokens"]
                )
                
                # In a real implementation, you would store the result in a database
                # and potentially notify the user through a websocket
                print(f"Generated code for request {body['request_id']}")
                print(code)
                
            except Exception as e:
                print(f"Error processing message: {e}")
                # In a real implementation, you would update the request status to "failed"
                # and store the error message

    async def run(self):
        await self.connect_rabbitmq()
        
        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                await self.process_message(message)

async def main():
    agent = CodeGenerationAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())