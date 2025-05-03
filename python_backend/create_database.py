import parse_html
import vector_index

from dotenv import load_dotenv
import os
#for pdf
import requests
import fitz  # PyMuPDF
from io import BytesIO

import pymongo

def create_database(html_file_name:str, database_name:str, collection_name:str):
    load_dotenv()

    DATABASE_LOGIN = os.getenv("DATABASE_LOGIN") #DATABASE_LOGIN is in the form username:password

    uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"

    # connect to your Atlas cluster
    client = pymongo.MongoClient(uri)

    database = client[database_name]

    collection = database[collection_name]

    data = parse_html.parse_html(html_file_name)

    i = 1

    for law in data:
        print(i)
        i += 1

        url = law["pdf"]   
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status

        pdf_data = BytesIO(response.content)
        doc = fitz.open(stream=pdf_data, filetype="pdf")

        full_text = ""
        for page in doc:
            full_text += page.get_text()

        law["pdf"]  = full_text
        doc.close()
    

    collection.insert_many(data)

    vector_index.initalize_vector_index(database_name, collection_name)

    client.close()

#create_database("bylaws.html","bylaws","1-304")