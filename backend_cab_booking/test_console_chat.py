"""
Quickest possible sanity check: talk to Ashad's LLM + tools in your terminal as plain text,
with no audio, no Telnyx, no ngrok. Useful for testing your LLM provider connectivity and the
Supabase booking tools before you touch the voice pipeline at all.

Run:
    python test_console_chat.py

Type 'quit' to exit.
"""

import asyncio
import os

from dotenv import load_dotenv

from prompts import CAB_BOOKING_SYSTEM_PROMPT

load_dotenv(override=False)


async def main():
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    print(f"Using LLM_PROVIDER={provider}\n")

    if provider == "openai":
        import openai

        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL", "gpt-5.4-2026-03-05")

        async def ask(messages):
            # Uses OpenAI's Responses API (client.responses.create) rather than the older
            # chat.completions endpoint.
            input_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
            resp = await client.responses.create(model=model, input=input_text)
            return resp.output_text

    else:  # anthropic
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

        async def ask(messages):
            # anthropic wants system separate from the messages list
            resp = await client.messages.create(
                model=model,
                max_tokens=300,
                system=CAB_BOOKING_SYSTEM_PROMPT,
                messages=[m for m in messages if m["role"] != "system"],
            )
            return resp.content[0].text

    messages = [{"role": "system", "content": CAB_BOOKING_SYSTEM_PROMPT}]
    print("Ashad is ready. Type your message (or 'quit' to exit).\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        messages.append({"role": "user", "content": user_input})
        reply = await ask(messages)
        messages.append({"role": "assistant", "content": reply})
        print(f"Ashad: {reply}\n")


if __name__ == "__main__":
    asyncio.run(main())