#!/usr/bin/env python3

import os, re
from bs4 import BeautifulSoup
import urllib.request

env_vars = {
    'steam_user'                    : 'STEAM_USER',
    'price_threshold'               : 'STEAM_MAX_PRICE',
    'low_price_discount_threshold'  : 'STEAM_LOW_PRICE_DISCOUNT',
    'discount_threshold'            : 'STEAM_MIN_DISCOUNT'
}

def __is_game_applicable(g, max_price, low_price_discount, min_discount, exclude):
    if g['gameid'] not in exclude:
        if g['finalPrice'] <= max_price:
            if g['originalPrice'] <= max_price:
                if g['discount'] >= low_price_discount:
                    return True
            else:
                return True
        elif g['discount'] >= min_discount:
            return True
    return False

def parse_in_file(in_file):
    inf = open(in_file, 'r')
    in_strings = inf.readlines()
    inf.close()

    glist = []
    for l in in_strings:
        lv = l[:-1].split(" ")
        g = {
            'gameid' : lv[0],
            'originalPrice' : float(lv[1]),
            'finalPrice' : float(lv[2]),
            'discount' : int(lv[3]),
            'link' : lv[4],
            'name' : " ".join(lv[5:])
        }
        glist.append(g)

    return glist

def get_discount_games(exclude=None, max_price=None, low_price_discount=None, min_discount=None, in_file=None, out_file=None):
    for var in env_vars.values():
        if var not in os.environ:
            print(var+" environment variable missing!")
            exit(1)

    if max_price is None:
        max_price = float(os.environ[env_vars['price_threshold']].replace(",", "."))

    if low_price_discount is None:
        low_price_discount = int(float(os.environ[env_vars['low_price_discount_threshold']].replace(",", ".")))

    if min_discount is None:
        min_discount = int(float(os.environ[env_vars['discount_threshold']].replace(",", ".")))

    if exclude is None:
        exclude = []

    discount_games = []

    if in_file is None or not os.path.isfile(in_file):
        url = "http://steamcommunity.com/id/{}/wishlist".format(os.environ[env_vars['steam_user']])
        soup = BeautifulSoup(urllib.request.urlopen(url), "lxml")
        wish_games = soup.findAll("div", "wishlistRowItem")

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
                discount_games.append(g)

    else:
        discount_games = parse_in_file(in_file)

    if out_file is not None:
        out_strings = []
        for g in discount_games:
            out_strings.append("{} {} {} {} {} {}\n".format(g['gameid'], g['originalPrice'], g['finalPrice'], g['discount'], g['link'], g['name']))

        if os.path.isfile(out_file):
            mode = "w"
        else:
            mode = "x"
        of = open(out_file, mode)
        of.writelines(out_strings)
        of.close()

    applicable_games = []
    for g in discount_games:
        if __is_game_applicable(g, max_price, low_price_discount, min_discount, exclude):
            applicable_games.append(g)

    return applicable_games

def format_game_info(game):
    return "{}\nprice: {}€ ({}€ - {}%)\nStore page: {}".format(game['name'], game['finalPrice'], game['originalPrice'], game['discount'], game['link'])

def print_game_list(games):
    if games is None or len(games) <= 0:
        print("No games in list")
    else:
        for g in games:
            print(format_game_info(g))

def get_stats(in_file=None):
    user = os.environ[env_vars['steam_user']]
    max_price = float(os.environ[env_vars['price_threshold']].replace(",", "."))
    low_price_discount = int(float(os.environ[env_vars['low_price_discount_threshold']].replace(",", ".")))
    min_discount = int(float(os.environ[env_vars['discount_threshold']].replace(",", ".")))

    in_file_stat = ""
    if in_file is not None:
        l = parse_in_file(in_file)
        in_file_stat = "\nlocal cached games = {}".format(len(l))

    return "user = {}\nmax_price = {}\nlow_price_discount = {}\nmin_discount = {}{}".format(user, max_price, low_price_discount, min_discount, in_file_stat)

if __name__ == '__main__':
     print_game_list(get_discount_games())
