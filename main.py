#!/usr/bin/env python3

import os, re
from steamwebapi import profiles
from bs4 import BeautifulSoup
import urllib.request

env_vars = {
    'api_key' : 'STEAM_API_KEY',
    'mail_dest' : 'STEAM_MAIL_DEST',
    'steam_user' : 'STEAM_USER'
}

for var in env_vars.values():
    if var not in os.environ:
        print(var+" environment variable missing!")
        exit(1)

try:
    user_profile = profiles.get_user_profile(os.environ[env_vars['steam_user']])
except:
    print("invalid user reference "+os.environ[env_vars['steam_user']])

"""Retrieves all appids for games on a user's wishlist (scrapes it, no API call available)."""
url = "http://steamcommunity.com/profiles/{}/wishlist".format(user_profile.steamid)
soup = BeautifulSoup(urllib.request.urlopen(url), "lxml")
wish_games = soup.findAll("div", "wishlistRowItem")

discount_games = []

for game in wish_games:
    if game.find("div", "discount_final_price") is not None:
        discount_games.append({
            'originalPrice': float(game.find("div", "discount_original_price").text[:-1].replace(",", ".")),
            'finalPrice': float(game.find("div", "discount_final_price").text[:-1].replace(",", ".")),
            'discount': game.find("div", "discount_pct"),
            'name': game.find("h4", "ellipsis").text,
            'link': game.find("a", "btnv6_blue_hoverfade")['href']
        })

for g in discount_games:
    print("{}: original price = {}€, discount price = {}€, discount amount = {}, store page = {}".format(g['name'], g['originalPrice'], g['finalPrice'], g['discount'], g['link']))