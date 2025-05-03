import base64
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
'''
prompt:str, bylaws_list: list###
'''
def generate():
    load_dotenv()
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.0-flash-lite"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""am I able to have a barbaque on my back deck"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        temperature = 0,
        top_p= 0.95,
        top_k=40,
        max_output_tokens= 8192,
        system_instruction= "you are someone who knows about all the by laws in Toronto Ontario. " \
        "Your task is to take in the data that is given to you and word it in a way to make it more " \
        "understandable to someone who doen't know much about laws",
    )
    print("These are the relivent by laws in Toronto:\n")

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")
if __name__ == "__main__":
    generate()
