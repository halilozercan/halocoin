Halocoin
=============

*In production*

![this is real, ok?](http://i.imgur.com/lz7hOlC.gif)

## What is this?

Halocoin is my personal project to learn, experiment and build around blockchain technology. This project is by no means production ready or close to actual implementation of Bitcoin protocol.
However, I have tried to imitate what is proposed in Bitcoin white paper.

Although source code is not related to original repository anymore and I already removed the fork tag, I want to acknowledge my initial start point. I thank zack-bitcoin for putting effort into
developing a minimal blockchain.

Objectives of this project:
- Readable code
- Modular services that explains how blockchain functions
- CLI or GUI to experiment with a cryptocurrency.
- Enable people to learn and share knowledge on blockchain, what is real innovation in Bitcoin.

Blockchain services include:

- Account : Take care of caching blockchain transactions and client-side data.
- Blockchain : Schedule adding, deleting, forking on blockchain
- API : Answer requests coming from client
- Peers Check : Regularly check known peers to stay up-to-date
- Peer Listen : Listen to other peers who are checking

It is important that account, blockchain, api and peers check services are working correctly.


## Getting started

Halocoin is packaged by easy_install that is supported by PyPI. As like any other python project,
I recommend you to install this on a virtualenv.

```
git clone https://github.com/halilozercan/halocoin
cd halocoin
virtualenv venv
source venv/bin/activate
python setup.py install
```

or

```
pip install halocoin
```

## How to run

```cli.py``` module offers a cool CLI to interact with the blockchain engine. When you install this package, you can call this module by 'halocoin' executable.
However, this CLI does not daemonize the engine when you start it. Instead users are free to choose from any daemonization methods that they
prefer (supervisor, nohup, screen, etc..)

You can start the client by running

```
halocoin start
```

Every service associated with blockchain runs at startup. This implies that your client will immediately start synchronizing with p2p network.
Initial peer list is hard-coded into client but you can update this list by updating your config file. Config file can be specified at startup or can be edited manually after first start.
Default data folder is inside your home directory and named ```.halocoin```.

## How to use

To interact with blockchain, you need to have an account, a wallet. You can create a wallet by running
```
halocoin new_wallet --wallet wallet_name
```

or by making an HTTP request to (GET or POST)

```
http://localhost:7001/new_wallet
Necessary parameters: wallet_name, password
```

If you prefer CLI, you will be prompted to enter the password that is going to be used for encryption of the wallet. This password prompt will always pop up when you use your wallet if you do not set a default wallet.