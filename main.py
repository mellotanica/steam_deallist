#!/usr/bin/env python3

import os, re
from steamwebapi import profiles
from bs4 import BeautifulSoup
import urllib.request

env_vars = {
    'api_key' : 'STEAM_API_KEY',
    'steam_user' : 'STEAM_USER',
    'price_threshold' : 'STEAM_MAX_PRICE',
    'discount_threshold' : 'STEAM_MIN_DISCOUNT'
}

for var in env_vars.values():
    if var not in os.environ:
        print(var+" environment variable missing!")
        exit(1)

max_price = float(os.environ[env_vars['price_threshold']].replace(",", "."))
min_discount = int(float(os.environ[env_vars['discount_threshold']].replace(",", ".")))

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
        g = {
            'originalPrice': float(game.find("div", "discount_original_price").text[:-1].replace(",", ".")),
            'finalPrice': float(game.find("div", "discount_final_price").text[:-1].replace(",", ".")),
            'discount': int(float(game.find("div", "discount_pct").text[1:-1].replace(",", "."))),
            'name': game.find("h4", "ellipsis").text,
            'link': game.find("a", "storepage_btn_alt")['href']
        }
        tokens = g['link'].split('/')
        g['gameid'] = tokens[len(tokens) - 1]
        if g['finalPrice'] <= max_price:
            if g['originalPrice'] <= max_price:
                if g['discount'] >= min_discount:
                    discount_games.append(g)
            else:
                discount_games.append(g)


for g in discount_games:
    print("{}: original price = {}€, discount price = {}€, discount amount = {}%, store page = {}".format(g['name'], g['originalPrice'], g['finalPrice'], g['discount'], g['link']))