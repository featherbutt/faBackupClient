import sys
import os
import pathlib
import time
import string
import random
import io
import urllib.parse

import requests
import ipfshttpclient

from ipfshttpclient.exceptions import ErrorResponse as IpfsError

hostName = os.environ['HOSTNAME']
secret = os.environ['SECRET']

headers = {'Authorization': f"Bearer {secret}"}

jsonHeaders ={
    'Content-type':'application/json', 
	'Authorization': f"Bearer {secret}"
}

proxies = {
	'http' : "socks5h://tor:9050",
	'https' : "socks5h://tor:9050"
}

def getCommand(url: str, headers=headers, **kwargs):
	while True:
		response = try_until_success(requests.get, f"get {url}")(url, headers=headers, **kwargs)
		if response.status_code != 200:
			print(f"Failed to get {url}, sleeping for 30 seconds")
			time.sleep(30)
			continue
		return response.json()
	
def get(url: str, headers=headers, **kwargs):
	while True:
		response = try_until_success(requests.get, f"get {url}")(url, **kwargs)
		if response.status_code != 200:
			print(f"Failed to get {url}, sleeping for 30 seconds: {response}")
			time.sleep(30)
			continue
		return response

def post(url: str, data: dict, headers=jsonHeaders):
	while True:
		response = try_until_success(requests.post, f"post {url}")(url, json=data, headers=headers)
		if response.status_code != 200:
			print(f"Failed to post {url}, sleeping for 30 seconds")
			time.sleep(30)
			continue
		return

def try_until_success(request, name="request"):  
    def inner(*args, **kwargs):
        while True:
            try:
                return request(*args, **kwargs)
            except Exception as e:
                print(f"Failed to {name}, sleeping for 30 seconds: {e}")
                time.sleep(30)
                continue
    return inner


def gen_rand_char() -> str:
    char_set = string.ascii_uppercase + string.digits
    return (''.join(random.sample(char_set*6, 6)))
	
client = ipfshttpclient.Client("/dns/ipfs/tcp/5001")

# Fetching new files
## Fetching new files from TOR
## Client receives an artist name and a list of urls, and the current IPFS hash for that folder.
## Client creates that folder but does not do a deep fetch.
## Client gets list of files already in the IPFS folder
## Client queries each url not already in the folder and adds the results to the folder.
## Client responds with the artist and the new folder hash
## Server queries the new folder hash

def ipfsFolderExists(path: str):
    def inner():
        try:
            return client.files.stat(path)
        except IpfsError:
            return None
    return try_until_success(inner, f"check exists {path}")()

def mergeDirectories(mergePath, *hashes):
	entryLists = [try_until_success(client.dag.get, "dag get 91")(hash)['Links'] for hash in hashes]
	# Pick the largest entry list to use as a base
	largestIdx = max(enumerate(entryLists), key = lambda x : len(x[1]))[0]
	combinedEntries = entryLists.pop(largestIdx)
	largestHash = hashes[largestIdx]
	nonce = gen_rand_char()
	try_until_success(client.files.cp, "cp 97")(f"/ipfs/{largestHash}", f"/scratch/{nonce}", opts={"parents":True})
	existingNames = {entry['Name']: entry['Hash']['/'] for entry in combinedEntries}
	for entryList in entryLists:
		for entry in entryList:
			if entry['Name'] in existingNames:
				if entry['Hash']['/'] != existingNames[entry['Name']]:
					# Conflict. How to handle this? Log with the server probably.
					post(f'https://{hostName}/flagDuplicate/', {'name': entry['Name'], 'hash1': entry['Hash']['/'], 'hash2': existingNames[entry['Name']]})
			else:
				existingNames[entry['Name']] = entry['Hash']['/']
				try_until_success(client.files.cp, "cp 107")(f"/ipfs/{entry['Hash']['/']}", f"/scratch/{entry['Name']}")
	try_until_success(client.files.rm, "rm 108",)(mergePath, recursive=True)
	try_until_success(client.files.mv, "mv 109")(f"/scratch/{nonce}", mergePath, opts={"parents":True})

start_time = time.time_ns()
if __name__ == "__main__":
	if os.environ.get('WAIT') is not None:
		exit(0)
	tor_time_ns = 0
	cpu_time_ns = 0
	submissions = 0
	while True:
		nextArtist = getCommand(f'https://{hostName}/nextTorArtist')
		if nextArtist['done']:
				break
		artist = nextArtist['name']
		urls = nextArtist['urls']
		folderHash = nextArtist['folderHash']
		folderAddress = f'/ipfs/{folderHash}'
		first_letter = artist[0]
		if not (first_letter.isalnum()):
			first_letter = "_"
		folderPath = f'/furaffinity/artist/{first_letter}/{artist}'
		if (stat := ipfsFolderExists(folderPath)) is not None:
			localHash = stat['Hash']
			if localHash != folderHash:
				print(f"merging folders for {artist}: {localHash} and {folderHash}")
				mergeDirectories(f'/furaffinity/artist/{first_letter}/{artist}', localHash, folderHash)
			else:
				print(f"found existing folder for {artist}: {localHash}")
		else:
			print(f"copying existing folder from server for {artist}: {folderHash}")
			try_until_success(client.files.cp, "cp 134")(folderAddress, folderPath, opts={"parents":True})
		existingFiles = try_until_success(client.files.ls, "ls 135")(folderPath)['Entries']
		if existingFiles is None:
			existingFileSet = set()
		else:
			existingFileSet = {x['Name'] for x in existingFiles}
		print(f"{artist}: Existing files: {len(existingFileSet)}")
		count = 0
		for path, baseName in urls:
			if path is None:
					path = ''
			if baseName.endswith('/'):
					continue
			if baseName in existingFileSet:
					continue
			count += 1
			baseNameEncoded = urllib.parse.quote(baseName, safe='/', encoding=None, errors=None)
			print(f'{count}: http://g6jy5jkx466lrqojcngbnksugrcfxsl562bzuikrka5rv7srgguqbjid.onion/fa/{artist}/{path}/{baseNameEncoded}')
			tor_start_time = time.time_ns()
			response = get(f'http://g6jy5jkx466lrqojcngbnksugrcfxsl562bzuikrka5rv7srgguqbjid.onion/fa/{artist}/{path}/{baseNameEncoded}', proxies=proxies)
			tor_time_ns += time.time_ns() - tor_start_time
			responseFile = io.BytesIO(response.content)
			ipfs_start_time = time.time_ns()
			hash = try_until_success(client.add, "add 151")(responseFile, raw_leaves=True, pin=False)['Hash']
			cpu_time_ns += time.time_ns() - ipfs_start_time
			submissions += 1
			if submissions % 10 == 0:
				elapsed_time = time.time_ns() - start_time
				print(f"Avg Tor time: {tor_time_ns/1e9/submissions}\nAvg CPU time: {cpu_time_ns/1e9/submissions}\n Avg total time: {elapsed_time/1e9/submissions}")
			if hash == "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku":
				print(f"FAILED to add {baseName}")
				continue
			print(f"{count}: created /ipfs/{hash}")
			fileAddress = f'/ipfs/{hash}'
			filePath = f'/furaffinity/artist/{first_letter}/{artist}/{baseName}'
			def copy():
				if ipfsFolderExists(filePath) is None:
					client.files.cp(fileAddress, filePath, opts={"parents":True})
			try_until_success(copy, "cp 154")()
			print(f"{count}: copied into /furaffinity/artist/{first_letter}/{artist}/{baseName}")
			
			if count % 100 == 0:
				newHash = try_until_success(client.files.stat, "stat 156")(folderPath, opts={"hash":True})['Hash']
				print("sending new artist hash to server: ", newHash)
				post(f'https://{hostName}/updateTorArtist/{artist}', {'newHash': newHash, 'id': os.environ['PRIVATE_PEER_ID']})
		newHash = try_until_success(client.files.stat, "stat 156")(folderPath, opts={"hash":True})['Hash']
		print(f"new hash for {artist}: {newHash}")
		

		post(f'https://{hostName}/finishTorArtist/{artist}', {'newHash': newHash, 'id': os.environ['PRIVATE_PEER_ID']})