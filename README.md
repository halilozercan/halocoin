Halocoin
=============

*In development*

![this is real, ok?](http://i.imgur.com/lz7hOlC.gif)

## What is this?

Halocoin is my personal project to learn, experiment and build around blockchain technology. This project is by no means production ready or close to actual implementation of Bitcoin protocol.
However, I have tried to imitate what is proposed in Bitcoin white paper. For example, it is still missing Merkle Trees for transactions which is a core property of Bitcoin.

Although source code is not related to original repository anymore and I already removed the fork tag, I want to acknowledge my initial start point. I thank zack-bitcoin for putting effort into
developing a minimal blockchain.

Objectives of this project:
- Readable code
- Modular services that explains how blockchain functions
- Blockhain is a consensus protocol between peers. How does client side handle everything?
- CLI or GUI to experiment with a cryptocurrency.
- Enable people to learn and share knowledge on blockchain, which is the real innovation of Bitcoin.

Blockchain services include:

- State : Take care of caching blockchain transactions and client-side data. Answers the question: What is the state right now?
- Blockchain : Schedule adding, deleting, forking on blockchain
- API : Answer requests coming from client
- Peers Check : Regularly check known peers to stay up-to-date
- Peer Listen : Listen to other peers who are checking


## Getting started

Halocoin is packaged according to distutils guidelines that is supported by PyPI. As like any other python project,
I recommend you to install this on a virtualenv.

Also, Halocoin only works and tested on Python 3 and above.

```
git clone https://github.com/halilozercan/halocoin
cd halocoin
virtualenv venv -p python3
source venv/bin/activate
python3 setup.py install
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
Default data folder is inside your home directory and named ```.halocoin```. You can defined another data folder by ```--dir``` option. Details of CLI are given above.

## How to use

As mentioned, halocoin comes with a minimalistic CLI but all it does is converting your command lines request into HTTP requests. Then, it sends these requests
to the running Restful API. If you prefer, you can use this API with another client.

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

## More documentation coming soon!!

Since CLI is not ready and UI is ported from another project originated from this repository, I prefer to use Restful API to talk with the client.

#### List of wallets
```http://localhost:7001/wallets```

#### New Wallet:
```http://localhost:7001/new_wallet```

Query Parameters:
- wallet_name : String
- password : String
- set_default : boolean <Set this wallet as default upon creation>

#### Blockcount:
```http://localhost:7001/blockcount```

#### Info Wallet:
```http://localhost:7001/info_wallet```

Returns information about a wallet. Address, public key, current balance and etc. If no parameters are given, client will return information about current default wallet. If it does not exist, an error will be thrown.

Query Parameters:
- wallet_name : String
- password : String

#### Mempool
```http://localhost:7001/mempool```

Transactions that are waiting in the pool

#### Blocks
```http://localhost:7001/blocks```

Query Parameters:
- start : int
- end : int

#### Balance
```http://localhost:7001/balance```

Query Parameters:
- address : String

#### Send
```http://localhost:7001/send```

Send halocoins to another address.

Query Parameters:
- address : String
- amount : int
- wallet_name : String
- password : String
- message : String optional