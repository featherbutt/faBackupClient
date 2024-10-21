# In a loop:
# Call nextBatch() to get the next batch of data
# Run FALR to create a local DB
# Upload it

import sys
import requests
from requests.exceptions import SSLError
import os
import string
import random
import subprocess
import sqlite3
import time

_, hostName, secret, a, b, batchSize = sys.argv

headers = {'Authorization': f"Bearer {secret}"}

def get(url: str):
    response = requests.get(url, headers=headers)
    while response.status_code != 200:
        print(f"Failed to get {url}, sleeping for 30 seconds")
        time.sleep(30)
        response = requests.get(url, headers=headers)

    return response.json()

def post(url: str, data: dict):
    while True:
        try:
            response = requests.post(url, data=data, headers=headers)
            if response.status_code != 200:
                print(f"Failed to post {url}, sleeping for 30 seconds")
                time.sleep(30)
                continue
        except SSLError:
                print(f"Failed to post {url}, sleeping for 30 seconds")
                time.sleep(30)
                continue
        break




def gen_rand_char() -> str:
    char_set = string.ascii_uppercase + string.digits
    return (''.join(random.sample(char_set*6, 6)))

def get_last_id(dbName):
    db = sqlite3.connect(dbName)
    cursor = db.cursor()
    cursor.execute('''
        SELECT id FROM submissions order by id desc limit 1;
    ''')
    ids = cursor.fetchall()
    db.close()
    if len(ids) == 0:
        return None
    return ids[0][0]

def initDb(dbName: str):
    subprocess.run(['falocalrepo', 'init', '--database', dbName])
    subprocess.run(['falocalrepo', 'config', 'cookies', '--database', dbName, '-c', 'a', a, '-c', 'b', b])

def uploadSubmissions(ids: list[int]):
    dbName = f'./dbs/FA_list_{gen_rand_char()}.db'

    initDb(dbName)

    RETRIES = 2
    for i in range(RETRIES):
        result = subprocess.run(['falocalrepo', 'download', 'submissions', '--database', dbName, *(str(i) for i in ids)])
        if result.returncode == 0:
            break
        newMax = get_last_id(dbName)
        if newMax is None:
            ids = (id for id in ids if id > newMax)
    else:
        print(f"Failed to download list")
        return False
    
    with open(dbName, 'rb') as f:
        post(f'https://{hostName}/upload/list/', data=f)
        print("Uploaded list")

def uploadRange(min, max):

    dbName = f'./dbs/FA_{min}_{max}_{gen_rand_char()}.db'

    initDb(dbName)
    
    newMin = min
    RETRIES = 3
    attempt = 1
    while attempt <= RETRIES:
        result = subprocess.run(['falocalrepo', 'download', 'range', '--database', dbName, newMin, max])
        print(result.stderr)
        print(result.stdout)
        if result.returncode == 0:
            break
        
        lastId = str(get_last_id(dbName))
        if lastId is None:
            lastId = min
        if lastId == newMin:
            attempt += 1
        else:
            attempt = 1
    else:
        print(f"Failed to download {min} to {max}")
        return False
    
    with open(dbName, 'rb') as f:
        post(f'https://{hostName}/upload/range/{min}/{max}', data=f)
        print("Uploaded range {min} to {max}")
    

def uploadArtist(artist):
    # artists_str = '_'.join(artists)
    dbName = f'./dbs/FA_{artist}_{gen_rand_char()}.db'

    initDb(dbName)

    #artist_tags = [tag for artist in artists for tag in ['-u', artist]]
    RETRIES = 2
    for i in range(RETRIES):
        result = subprocess.run(['falocalrepo', 'download', 'users', '-u', artist,
                                 '-f', 'gallery', '-f', 'scraps', '-f', 'journals', '-f', 'userpage', '--database', dbName])
        if result.returncode == 0:
            break
        newMax = get_last_id(dbName)
        if newMax is None:
            newMax = artist
    else:
        print(f"Failed to download artist {artist}")
        return False
    
    with open(dbName, 'rb') as f:
        post(f'https://{hostName}/upload/artist/{artist}', data=f)
        print(f"Uploaded artist {artist}")
    
    
while True:
    nextBatch = get(f'https://{hostName}/nextBatch/{batchSize}')
    if nextBatch["done"]:
        break
    
    print(nextBatch)
    match nextBatch["type"]:
        case "list":
            uploadSubmissions(nextBatch["ids"])
        case "range":
            uploadRange(str(nextBatch["min"]), str(nextBatch["max"]))
        case "artist":
            uploadArtist(nextBatch["artist"])
        case _:
            print("Unknown batch type")
            break