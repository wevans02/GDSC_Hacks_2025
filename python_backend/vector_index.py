#for git
from dotenv import load_dotenv
import os
#pymango
from pymongo.mongo_client import MongoClient
from pymongo.operations import SearchIndexModel
#other
import time


#this function take the name of the database and the collection on the mongo database and initializes the vector data
def initalize_vector_index(database_name:str, collection_name:str):

  load_dotenv()

  DATABASE_LOGIN = os.getenv("DATABASE_LOGIN") #DATABASE_LOGIN is in the form username:password

  uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"

  # Create a new client and connect to the server
  client = MongoClient(uri)

  # Access your database and collection
  database = client[database_name]
  collection = database[collection_name]

  # Create your index model, then create the search index
  search_index_model = SearchIndexModel(
    definition={
      "fields": [
        {
          "type": "vector",
          "path": "plot_embedding",
          "numDimensions": 1536,
          "similarity": "dotProduct",
          "quantization": "scalar"
        }
      ]
    },
    name="vector_index",
    type="vectorSearch"
  )

  result = collection.create_search_index(model=search_index_model)
  print("New search index named " + result + " is building.")

  # Wait for initial sync to complete
  print("Polling to check if the index is ready. This may take up to a minute.")
  predicate=None
  if predicate is None:
    predicate = lambda index: index.get("queryable") is True

  while True:
    indices = list(collection.list_search_indexes(result))
    if len(indices) and predicate(indices[0]):
      break
    time.sleep(5)
  print(result + " is ready for querying.")

  client.close()