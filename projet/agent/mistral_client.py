import os
from mistralai import Mistral
from .config import model

def request_mistral_model(messages: list[dict]) -> str:
    """
    Makes a request to the Mistral AI model.

    Args:
        messages: A list of message dictionaries in the format
                  {"role": "system"/"user", "content": "message"}.

    Returns:
        The content of the model's response.
    """
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    resp = client.chat.complete(
        model=os.environ.get("MODEL", model),
        messages=messages,
    )
    raw_content = resp.choices[0].message.content.strip()
    return raw_content

    