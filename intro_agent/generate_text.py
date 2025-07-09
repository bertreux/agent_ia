import os
from mistralai import Mistral

api_key = os.environ["MISTRAL_API_KEY"]
model = "mistral-large-latest"

def generateText(prompt: str) -> str:
    client = Mistral(api_key=api_key)

    chat_response = client.chat.complete(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )

    return chat_response.choices[0].message.content;

if __name__ == "__main__":
    print(generateText("Quel est le plus grand océan du monde ?"))
