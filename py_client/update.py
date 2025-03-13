import requests

endpoint = 'http://localhost/house/1/update'
data={
    'price':30000
}
get_response = requests.put(endpoint, json=data)
print(get_response.json())
print(get_response.status_code)
                            