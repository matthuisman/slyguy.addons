import requests

test = requests.get('http://104.21.88.162', headers={'host': 'i.mjh.nz'}, verify=False)
print(test.text)