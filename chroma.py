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

        documents = ""
        for message in messages:
            documents += f"{message[0]}: {message[1]}"
            documents += "\n"

        self.collection.add(
            documents=documents,
            ids=f"{self.last_id + 1}"
        )
        self.last_id += 1

        db.save("last_id", self.last_id)

    def query(self, query, context_pairs):
        context = "\n".join(["{}: {}".format(author, message) for author, message in context_pairs])
        return self.collection.query(
            query_texts=[context, query],
            include=["documents"],
            n_results=3
        )["documents"][0]
