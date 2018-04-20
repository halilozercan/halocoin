"""
This file is intended for testing purposes on Alkanlab servers

- New wallet named `test`
- Check whether 'test' is created successfully
- Make 'test' default wallet
- Check whether 'test' is made default
- Get score of wallet.
  - If score is 0, make pool registration
- Get application of wallet.
  - If no application, make coinami continuous application
"""

import requests
wallets = requests.get("http://0.0.0.0:7001/wallet/list").json()['wallets']
if 'test' not in wallets:
    print('test wallet does not exist. Creating...')
    requests.post("http://0.0.0.0:7001/wallet/new",
                  data={'wallet_name': 'test', 'password': '3'})

wallets = requests.get("http://0.0.0.0:7001/wallet/list").json()['wallets']
if 'test' not in wallets:
    print('test wallet still does not exist. \nFAILED!')
    exit(1)

print('Logging in with test wallet')
jwtToken = requests.post('http://0.0.0.0:7001/login',
                         data={'wallet_name': 'test', 'password': '3'}).json()['jwt']
loggedin_wallet = requests.get('http://0.0.0.0:7001/login/info',
                               headers={"Authorization": "Bearer " + jwtToken}).json()
if loggedin_wallet['wallet']['name'] != 'test':
    print('Couldn\'t change default wallet. \nFAILED!')
    exit(1)

print('Starting power')
result = requests.post('http://0.0.0.0:7001/service/power/start',
                       data={'password': '3'},
                       headers={"Authorization": "Bearer " + jwtToken}).text
print(result)