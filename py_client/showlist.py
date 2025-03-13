import requests

endpoint = 'http://localhost/showlist'

get_response = requests.get(endpoint)

print(get_response.json())
print(get_response.status_code)