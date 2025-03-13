import requests

endpoint = 'http://localhost/create/'
data={
    'guests': 4
}
get_response = requests.post(endpoint, json=data)

print(get_response.json())
print(get_response.status_code)