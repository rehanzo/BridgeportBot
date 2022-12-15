from sqlitedict import SqliteDict

def save(key, value, cache_file="cache.sqlite3"):
    try:
        with SqliteDict(cache_file) as db:
            db[key] = value # Using dict[key] to store
            db.commit() # Need to commit() to actually flush the data
    except Exception as ex:
        print("Error during storing data (Possibly unsupported):", ex)

def load(key, cache_file="cache.sqlite3"):
    try:
        with SqliteDict(cache_file) as db:
            value = db[key] # No need to use commit(), since we are only loading data!
        return value
    except Exception as ex:
        print("Error during loading data:", ex)

def clear(key, cache_file="cache.sqlite3"):
    try:
        with SqliteDict(cache_file) as db:
            db.pop(key)
            db.commit() # Need to commit() to actually flush the data
    except Exception as ex:
        print("Error during loading data:", ex)

def keysList(cache_file="cache.sqlite3"):
    try:
        with SqliteDict(cache_file) as db:
            pre = "  - "
            finalStr = pre + ("\n" + pre).join(db.keys())
        return finalStr
    except Exception as ex:
        print("Error during loading data:", ex)
