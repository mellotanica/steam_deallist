#!/usr/bin/env python3

import os
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
from isthedeal_wrapper import get_multiple_games_lowest_prices
from userdata import UserData, Game
import re
import editdistance
import json

optional_vars = {
    'isthereanydeal_api_key': 'ISTHEREANYDEAL_API_KEY'
}


def __sanitize_price_string(price):
    return price.replace(",",".").replace("-", "0")


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


def get_updated_user_cache(user_data):
    if type(user_data) is not UserData:
        raise Exception("user_data must be a valid UserData object")

    url = "http://steamcommunity.com/id/{}/wishlist".format(user_data.username)
    soup = BeautifulSoup(urllib.request.urlopen(url), "lxml")

    data = None
    second_url = None
    for s in soup.findAll("script"):
        if 'var g_rgAppInfo' in s.text:
            for l in s.text.splitlines():
                if 'var g_rgAppInfo' in l:
                    start = min(l.index("{"), l.index("["))
                    end = max(l.rindex("}"), l.rindex("]")) + 1
                    data = json.loads(l[start:end])
                elif 'var g_strWishlistBaseURL' in l:
                    second_url = l[l.index('"')+1:l.rindex('"')].replace("\\/", "/") + "wishlistdata"
                if data is not None and second_url is not None:
                    break
            break

    if second_url is not None:
        req = urllib.request.urlopen(second_url)
        data.update(json.loads(req.read().decode(req.info().get_content_charset('utf-8'))))

    discount_games = {}

    for game in data.values():
        sub = None
        prc = None
        for s in game["subs"]:
            if s["discount_pct"] > 0 and (prc is None or s["price"]):
                sub = s
                prc = s["price"]

        if sub is not None:
            db = BeautifulSoup(sub["discount_block"], "lxml")
            original_price = float(__sanitize_price_string(db.find("div", "discount_original_price").text[:-1]))
            final_price = float(__sanitize_price_string(db.find("div", "discount_final_price").text[:-1]))
            cut = int(float(__sanitize_price_string(db.find("div", "discount_pct").text[1:-1])))
            name = game["name"]
            tokens = game["capsule"].split('/')
            gameid = "app/"+tokens[-2]
            link = "http://store.steampowered.com/" + gameid
            discount_games[gameid] = (Game(gameid, original_price, final_price, cut, link, name, None))

    if optional_vars['isthereanydeal_api_key'] in os.environ:
        id_list = [g.gid for g in discount_games.values()]

        deals = get_multiple_games_lowest_prices(os.environ[optional_vars['isthereanydeal_api_key']], id_list)

        if deals is not None:
            for d in deals:
                if d.game_id in discount_games:
                    discount_games[d.game_id].deal = d

    return discount_games.values()


def get_discount_games(user_data, max_price=None, low_price_discount=None,
                       min_discount=None, ignore_excludes=True, include_recommended=None):
    if type(user_data) is not UserData:
        raise Exception("user_data must be a valid UserData object")

    if max_price is None:
        max_price = user_data.configs.max_price

    if low_price_discount is None:
        low_price_discount = user_data.configs.low_price_min_discount

    if min_discount is None:
        min_discount = user_data.configs.min_discount

    exclude = user_data.get_exclude_map()
    if exclude is None or ignore_excludes:
        exclude = {}

    if include_recommended is None:
        include_recommended = user_data.configs.show_best_deals

    applicable_games = [g for g in user_data.cache if g.is_applicable(
        max_price, low_price_discount, min_discount, exclude, include_recommended)]

    return applicable_games


def get_id_from_store_url(link):
    link_frags = urllib.parse.urlsplit(link).path.split("/")
    return "/".join(link_frags[1:3])

__clean_spaces = re.compile(r"\s+")

def query_steam_for_game(name):
    global __clean_spaces
    name = __clean_spaces.sub(" ", name)
    if name.endswith(" Standard Edition"):
        name = name[:-len(" Standard Edition")]
    url = "http://store.steampowered.com/search/?term=" + urllib.parse.quote(name, safe='')
    soup = BeautifulSoup(urllib.request.urlopen(url), "lxml")
    minedit = None
    link = None

    for a in soup.find("div", id="search_result_container").findAll("a"):
        gref = a.find("div", "col search_name ellipsis")
        if gref is not None:
            clink = a.get('href')
            game_name = __clean_spaces.sub(" ", gref.span.text)
            distance = editdistance.eval(name, game_name)
            if minedit is None or distance < minedit:
                link = clink
                minedit = distance
            if distance == 0:
                break

    if link is not None and minedit < 4:
        return get_id_from_store_url(link), link
    return None, None


def print_game_list(games):
    if games is None or len(games) <= 0:
        print("No games in list")
    else:
        for g in games:
            print(g)


def get_stats(user_data):
    user = user_data.username
    max_price = user_data.configs.max_price
    low_price_discount = user_data.configs.low_price_min_discount
    min_discount = user_data.configs.min_discount
    in_file_stat = "\ncached games = {}".format(len(user_data.cache))

    return "user = {}\nmax_price = {}\nlow_price_discount = {}\nmin_discount = {}{}".format(
        user, max_price, low_price_discount, min_discount, in_file_stat)
