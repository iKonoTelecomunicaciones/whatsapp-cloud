# Whatsapp-cloud


Whatsapp business account Whatsapp-cloud <-> Matrix bridge built using [mautrix-python](https://github.com/mautrix/python)

This bridge is based on:

 - [Whatsapp bridge](https://github.com/iKonoTelecomunicaciones/whatsapp-cloud)


## Installation

The first step is to have an account on the whatsapp business platform. Then you must create a whatsapp application.

### Documentation

NOTE: This bridge is inspired by the mautrix bridges, so you can follow the documentation of these bridges.
[Bridge setup](https://docs.mau.fi/bridges/python/setup.html)
(or [with Docker](https://docs.mau.fi/bridges/general/docker-setup.html))

Docker image: `ikonoim/whatsapp-cloud:latest`

### Register a Whatsapp application on the bridge

- Create a room without encryption
- Then invite the bridge bot (you must have the user registered in the config section `bridge.permissions` as admin)
- Send the command `register-app <wb_app_name> <wb_phone_id> <token>`
- you can now start receiving incoming messages on the registered number


## Discussion

Matrix room:

[`#whatsapp-bridge:matrix.org`](https://matrix.to/#/#whatsapp-bridge:matrix.org)
