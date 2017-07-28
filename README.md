Mc-Chain
=============

*In production*

![this is real, ok?](http://i.imgur.com/lz7hOlC.gif)

# Wallet

Encrypted file that includes

- public keys
- private keys

Client can create many addresses by using different key pairs.

# Account

To keep track of transactions and money transfers, every address information is held in database in an account object.
An account object is under database with its key being the address itself.

Properties are:

- tx count
- balance
-