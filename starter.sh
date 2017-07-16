#!/bin/bash

# insert proper values

export STEAM_API_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
export STEAM_USER=XXXXXXXX
export STEAM_MAX_PRICE=5
export STEAM_MIN_DISCOUNT=50

python3 "$(dirname "${BASH_SOURCE[0]}")"/steam_deallist.py
