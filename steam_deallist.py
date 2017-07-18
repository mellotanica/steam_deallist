#!/usr/bin/env python3

import os, re
from steamwebapi import profiles
from bs4 import BeautifulSoup
import urllib.request

env_vars = {
    'api_key'                       : 'STEAM_API_KEY',
    'steam_user'                    : 'STEAM_USER',
    'price_threshold'               : 'STEAM_MAX_PRICE',
    'low_price_discount_threshold'  : 'STEAM_LOW_PRICE_DISCOUNT',
    'discount_threshold'            : 'STEAM_MIN_DISCOUNT'
}

def get_discount_games(exclude=None):
    for var in env_vars.values():
        if var not in os.environ:
            print(var+" environment variable missing!")
            exit(1)

    max_price = float(os.environ[env_vars['price_threshold']].replace(",", "."))
    low_price_discount = int(float(os.environ[env_vars['low_price_discount_threshold']].replace(",", ".")))
    min_discount = int(float(os.environ[env_vars['discount_threshold']].replace(",", ".")))

    if exclude is None:
        exclude = []

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
            if g['gameid'] not in exclude:
                if g['finalPrice'] <= max_price:
                    if g['originalPrice'] <= max_price:
                        if g['discount'] >= low_price_discount:
                            discount_games.append(g)
                    else:
                        discount_games.append(g)
                elif g['discount'] >= min_discount:
                    discount_games.append(g)

    return discount_games

def format_game_info(game):
    return "{}\nprice: {}€ ({}€ - {}%)\nStore page: {}".format(game['name'], game['finalPrice'], game['originalPrice'], game['discount'], game['link'])

def print_game_list(games):
    if games is None or len(games) <= 0:
        print("No games in list")
    else:
        for g in games:
            print(format_game_info(g))

def get_stats():
    user = os.environ[env_vars['steam_user']]
    max_price = float(os.environ[env_vars['price_threshold']].replace(",", "."))
    low_price_discount = int(float(os.environ[env_vars['low_price_discount_threshold']].replace(",", ".")))
    min_discount = int(float(os.environ[env_vars['discount_threshold']].replace(",", ".")))

    return "user = {}\nmax_price = {}\nlow_price_discount = {}\n,min_discount = {}".format(user, max_price, low_price_discount, min_discount)

if __name__ == '__main__':
     print_game_list(get_discount_games())
