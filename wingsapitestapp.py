import requests #Found at python-requests.org/
import json

url="https://tabletop.events/api"
api_key_id = '0A4DCD00-ED07-11E9-B27C-43B2D530A4B6' #Replace with yours
username = 'eric.boaen@theroleinitiative.o' #Replace with yours
password = 'Unobtainium1' #Replace with yours

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

# Fetch Group info
params = {'session_id': session['id']}
response = requests.get(url + "/group/B3124686-B852-11E8-AB7F-B79E49AF76B9/conventions", params=params)
data = response.json()
convention_count = 0
conventions = {}
print ("---Get Convention Info---")
for convention in data['result']['items']:
    toadd = {'Name': convention['name'], 'ID': convention['id']}
    conventions[convention_count]= toadd
    convention_count = convention_count + 1
print (conventions)
print("----------------------")

# Fetch Convention events
for con in conventions:
    print (con,conventions[con]['Name'])
while True:
    try:
        select_con = int(input("Select the convention: "))
        if select_con in range(convention_count):
            print("---Convention Information---")
            params = {'session_id': session['id'], '_include_relationships': '1'}
            response = requests.get(url + "/convention/" + conventions[select_con]['ID'], params=params)
            data = response.json()
            print("---Event Listing---")
            response = requests.get('https://tabletop.events' + data['result']['_relationships']['events'], params=params)
            data = response.json()
            for field in data['result']['items']:
                print (field['name'],field['_relationships']['eventhosts'])
#            for field in data['result']['items']:
#            for field in data['result']:
#                print (field, data['result']['items'][field])
#            print("----------------------")
            break
        if select_con == 99:
            break
    except:
        pass

    print ('\nIncorrect input, try again')
#for con_info in data:
#    conventions[con].update({'view_uri': data[con_info]['view_uri']})

# Fetch Convention info
# params = {'session_id': session['id']}
# response = requests.get(url + "/convention", params=params)
# print("---Get Convention info---")
# data = response.json()
# for convention in data['result']['items']:
#    print (convention['name'])
# print("----------------------")

# Upload a file
#params = {
#'name': 'example.png',
#'folder_id': root_folder_id,
#'session_id': session['id']
#}
#files = { 'file': open('example.png','rb') }
#response = requests.post(url + "/file", params=params, files=files)
#print("---Upload response---")
#print(response.json())
#print("---------------------")

# Search Games
#params = {
#'q' : 'Steampunk',
#'session_id': session['id'] #optional
#}
#response = requests.get(url + "/game", params=params)
#print("----- Results -----")
#print(response)
#print("------ Done! -------")
