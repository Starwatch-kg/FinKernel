import asyncio
from llm_agent import parse_transaction_with_llm

async def test():
    try:
        result = await parse_transaction_with_llm("купил кофе за 150 рублей")
        print("Success:", result)
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
