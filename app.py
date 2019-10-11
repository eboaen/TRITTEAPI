import requests #Found at python-requests.org/

url="https://www.thegamecrafter.com/api"
api_key_id = '' #Replace with yours
username = '' #Replace with yours
password = '' #Replace with yours

#Get a Session
params = {'api_key_id': api_key_id, 'username' : username, 'password': password}
response = requests.post(url + "/session", params=params)
if response.status_code==200:
  print("----Status code OK!----")
  print("---Get a session---")
  print(response.json())
  print("-------------------")
session = response.json()['result']

# Fetch my account info
params = {'session_id': session['id']}
response = requests.get(url + "/user/" + session['user_id'], params=params)
print("---Get account info---")
print(response.json())
print("----------------------")
user = response.json()['result']
root_folder_id = user['root_folder_id']

# Upload a file
params = {
'name': 'example.png',
'folder_id': root_folder_id,
'session_id': session['id']
}
files = { 'file': open('example.png','rb') }
response = requests.post(url + "/file", params=params, files=files)
print("---Upload response---")
print(response.json())
print("---------------------")

# Search Games
params = {
'q' : 'Steampunk',
'session_id': session['id'] #optional
}
response = requests.get(url + "/game", params=params)
print("----- Results -----")
print(response)
print("------ Done! -------")
