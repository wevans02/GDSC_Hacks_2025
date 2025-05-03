import base64
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
'''
prompt:str, bylaws_list: list###
'''
def generate_response(user_query, context_chunks):
    load_dotenv()
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    #print(context_chunks)

    # context chunks is list of dictionaries
    context_string = ''
    for law in context_chunks:
        print(law)
        context_string += "\n"  + law['pdf_content']
 
    model = "gemini-2.0-flash-lite"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=user_query),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        temperature = 1.0,
        top_p= 0.95,
        top_k=40,
        max_output_tokens= 8192,
        system_instruction="You are to help citizens understand local bylaws. Based ONLY on the following bylaw sections: [" + context_string + "] Please answer the user's question using only the information provided in the bylaw sections above. If the information is not present in the provided sections, state that the answer cannot be found in the provided context. Be concise and specific."
    )

    print("context: ",context_string)
    #print("\n\nabced\n\n")

    response =  client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    #print("\n\nthis ran\n\n")

    #print(response.text)
    return response.text