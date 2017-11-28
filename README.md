Halocoin
=============

*In production*

![this is real, ok?](http://i.imgur.com/lz7hOlC.gif)

## How to install

Halocoin is packaged by easy_install that is supported by PyPI. As like any other python project,
I recommend you to install this on a virtualenv.

```
git clone https://github.com/halilozercan/halocoin
cd halocoin
virtualenv venv
source venv/bin/activate
python setup.py install
```

## How to run

```cli.py``` module offers a cool CLI to interact with the blockchain engine.
However, this CLI does not daemonize the engine. Instead users are free to choose from any daemonization methods that they
prefer (supervisor, nohup, screen, etc..)

You can start the client by running

```
halocoin start
```

Every service associated with blockchain runs at startup. This implies that your client will immediately start synchronizing with p2p network.
Initial peer list is hard-coded into client but you can update this list by updating your config file.

```
halocoin new_wallet --wallet my_new_wallet
```

To interact with blockchain and have an account, one needs to create a wallet.
You will be prompted to enter the password that is going to be used for encryption of the wallet. This password prompt will always pop up when you use your wallet.
This is a security measure to make sure that clients always take care of their wallet.

Blockchain services include:

- Account : Take care of caching blockchain transactions.
- Blockchain : Schedule adding, deleting, forking on blockchain
- API : Answer requests coming from client
- Peers Check : Regularly check known peers to stay up-to-date
- Peer Listen : Listen to other peers who are checking

It is important that account, blockchain, api and peers check services are working correctly.

Then you can use ```halocoin``` to query your blockchain engine for simple stuff like balance, address information,
 blockcount.

### TODO:

- [ ] Add more information on README
- [ ] Prepare wiki pages to detail implementation and choices
- [ ] True p2p
- [ ] Unit tests to simulate peer interactions