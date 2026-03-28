"""
CLI tool for testing the email-agent backend.
Run the server first: uvicorn main:app --reload
Then run this script: python cli_test.py
"""

import httpx

BASE_URL = "http://localhost:8000"
SENDER = "+1234567890"


def send_command(message: str) -> dict:
    response = httpx.post(
        f"{BASE_URL}/sms",
        json={"sender": SENDER, "message": message},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main():
    print("Email Agent CLI — type your command or 'quit' to exit\n")

    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not message:
            continue
        if message.lower() in ("quit", "exit"):
            print("Goodbye.")
            break

        try:
            result = send_command(message)
            print(f"Agent: {result['reply']}\n")
        except httpx.ConnectError:
            print("Error: Could not connect. Is the server running? (uvicorn main:app --reload)\n")
        except httpx.HTTPStatusError as e:
            print(f"Error: {e.response.status_code} — {e.response.text}\n")


if __name__ == "__main__":
    main()
