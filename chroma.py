import chromadb
import db

class Chroma():
    client = None
    collection = None
    last_id = None

    def __init__(self):
        self.client = chromadb.PersistentClient(path="chroma/")
        self.collection = self.client.get_or_create_collection(name="messages") # Get a collection object from an existing collection, by name. If it doesn't exist, create it.
        last_id = db.load("last_id", "misc.sqlite3")
        self.last_id = 0 if not last_id else int(last_id)

    def addMessages(self, messages):
        # messages - list of (author, message) pairs
        ids = [f"{id}" for id in range(self.last_id + 1, len(messages) + 1)]
        print(ids)
        print(self.last_id)
        print(len(messages))
        self.last_id = ids[-1]

        metadatas = [{"author": message[0]} for message in messages]
        documents = [f"{message[0]}: {message[1]}" for message in messages]

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        # db.save("last_id", self.last_id)

    def query(self, query):
        return self.collection.query(
            query_texts=[query],
            include=["documents"],
            n_results=1
        )
