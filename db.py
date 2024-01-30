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
            if key.isnumeric():
                key = list(db.keys())[int(key)]
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
        finalStr = ""
        with SqliteDict(cache_file) as db:
            i = 0
            for key in list(db.keys()):
                pre = "{} - ".format(i)
                finalStr += pre + key + "\n"
                i += 1
        return finalStr
    except Exception as ex:
        print("Error during loading data:", ex)
