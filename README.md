Halocoin
=============

*In production*

![this is real, ok?](http://i.imgur.com/lz7hOlC.gif)

## How to install

Halocoin is prepared to be install by easy_install package that is supported by PyPI. As like any other python project,
I recommend you to install this on a virtualenv.

```
git clone https://github.com/halilozercan/halocoin
cd halocoin
virtualenv venv
source venv/bin/activate
python setup.py install
```

Or if you do not want to clone the whole repository, you can install by PyPI

```
pip install halocoin
```

## How to run

```cli.py``` module offers a cool CLI to interact with the blockchain engine.
However, this CLI does not daemonize the engine. Instead users are free to choose from any daemonization methods that they
like (supervisor, nohup, screen, etc..) To start the client, one needs a wallet

```
python cli.py new_wallet --wallet my_new_wallet
```

You will be prompted to enter your password. Halocoin uses AES encryption to protect your wallet files. After, successfully
creating your wallet, you can now run the blockchain engine.

```
python cli.py start --wallet my_new_wallet
```

You will again be prompted to enter the password for this wallet. This password prompt will always pop up when you start
your engine. This is a security measure to make sure that clients always take care of their wallet.

If everything goes smoothly, engine will start up and register necessary services to function. These services include:

- Account : Take care of caching blockchain transactions to right accounts.
- Blockchain : Schedule adding, deleting, forking on blockchain
- API : Answer requests coming from local client
- Peers Check : Regularly check known peers to stay updated
- Peer Listen : Listen to other peers who are checking

It is important that account, blockchain, api and peers check services are working correctly.

Then you can use ```cli.py``` to query your blockchain engine for simple stuff like balance, address information,
 blockcount.

### TODO:

- [ ] Add more information on README
- [ ] Prepare wiki pages to detail implementation and choices
- [ ] True p2p
- [ ] Unit tests to simulate peer interactions