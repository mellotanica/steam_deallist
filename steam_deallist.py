#!/usr/bin/env python3

import os, re
from bs4 import BeautifulSoup
import urllib.request
import json
from isthedeal_wrapper import Deal, get_multiple_games_lowest_prices

mandatory_vars = {
    'steam_user'                    : 'STEAM_USER',
    'price_threshold'               : 'STEAM_MAX_PRICE',
    'low_price_discount_threshold'  : 'STEAM_LOW_PRICE_DISCOUNT',
    'discount_threshold'            : 'STEAM_MIN_DISCOUNT'
}

optional_vars = {
    'isthereanydeal_api_key': 'ISTHEREANYDEAL_API_KEY'
}

env_vars = mandatory_vars.copy()
env_vars.update(optional_vars)


class Game:
    def __init__(self, gid, original_price, price, cut, link, name, deal):
        self.gid = gid
        self.original_price = original_price
        self.price = price
        self.cut = cut
        self.link = link
        self.name = name
        self.deal = deal


    def __str__(self):
        recommend = False
        str = "{}".format(self.name)
        str += "\nprice: {}€ ({}€ - {}%)".format(self.price, self.original_price, self.cut)
        if self.deal is not None:
            if self.deal.current.price == self.deal.historical.price:
                if self.deal.current.shop['id'] == 'steam':
                    recommend = True
                str += "\nLowest price: {}".format(self.deal.current)
            else:
                str += "\nLowest prices: current {}, all time {}".format(self.deal.current, self.deal.historical)
        str += "\nStore page: {}".format(self.link)
        if recommend:
            str += "\n💸💸💸Go buy it now!💸💸💸"
        return str

    def to_dict(self):
        d = {
            'game_id': self.gid,
            'original_price': self.original_price,
            'price': self.price,
            'cut': self.cut,
            'link': self.link,
            'name': self.name
        }
        if self.deal is not None:
            d['deal'] = self.deal.to_dict()
        else:
            d['deal'] = None
        return d

    def from_dict(ddata):
        if ddata is None:
            return None
        return Game(
            ddata['game_id'],
            ddata['original_price'],
            ddata['price'],
            ddata['cut'],
            ddata['link'],
            ddata['name'],
            Deal.from_dict(ddata['deal'])
        )

    def to_json(self):
        return json.dumps(self.to_dict())

    def from_json(jdata):
        if jdata is None:
            return None
        return json.loads(jdata)


def __is_game_applicable(g, max_price, low_price_discount, min_discount, exclude):
    if g.gid not in exclude:
        if g.price <= max_price:
            if g.original_price <= max_price:
                if g.cut >= low_price_discount:
                    return True
            else:
                return True
        elif g.cut >= min_discount:
            return True
    return False


def parse_in_file(in_file):
    inf = open(in_file, 'r')
    jdata = inf.read()
    inf.close()

    jobj = json.loads(jdata)
    glist = {}
    for j in jobj:
        g = Game.from_dict(j)
        glist[g.gid] = g

    return glist


def get_discount_games(exclude=None, max_price=None, low_price_discount=None, min_discount=None, in_file=None, out_file=None):
    for var in mandatory_vars.values():
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

    itd_api = None
    if optional_vars['isthereanydeal_api_key'] in os.environ:
        itd_api = os.environ[optional_vars['isthereanydeal_api_key']]

    discount_games = {}

    if in_file is None or not os.path.isfile(in_file):
        url = "http://steamcommunity.com/id/{}/wishlist".format(os.environ[env_vars['steam_user']])
        soup = BeautifulSoup(urllib.request.urlopen(url), "lxml")
        wish_games = soup.findAll("div", "wishlistRowItem")

        for game in wish_games:
            if game.find("div", "discount_final_price") is not None:
                original_price = float(game.find("div", "discount_original_price").text[:-1].replace(",", "."))
                final_price = float(game.find("div", "discount_final_price").text[:-1].replace(",", "."))
                cut = int(float(game.find("div", "discount_pct").text[1:-1].replace(",", ".")))
                name = game.find("h4", "ellipsis").text
                link = game.find("a", "storepage_btn_alt")['href']
                tokens = link.split('/')
                gameid = "/".join(tokens[-2:])
                discount_games[gameid] = (Game(gameid, original_price, final_price, cut, link, name, None))

        if itd_api is not None:
            id_list = [g.gid for g in discount_games.values()]

            deals = get_multiple_games_lowest_prices(itd_api, id_list)

            for d in deals:
                if d.game_id in discount_games:
                    discount_games[d.game_id].deal = d

    else:
        discount_games = parse_in_file(in_file)

    if out_file is not None:
        out_dicts = [g.to_dict() for g in discount_games.values()]

        if os.path.isfile(out_file):
            mode = "w"
        else:
            mode = "x"
        of = open(out_file, mode)
        of.write(json.dumps(out_dicts))
        of.close()

    applicable_games = []
    for g in discount_games.values():
        if __is_game_applicable(g, max_price, low_price_discount, min_discount, exclude):
            applicable_games.append(g)

    return applicable_games


def print_game_list(games):
    if games is None or len(games) <= 0:
        print("No games in list")
    else:
        for g in games:
            print(g)


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
