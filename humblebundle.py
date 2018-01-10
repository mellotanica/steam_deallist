#!/usr/bin/env python3

import isthedeal_wrapper
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
from userdata import Game
import re
import editdistance

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
        link_frags = urllib.parse.urlsplit(link).path.split("/")
        return "/".join(link_frags[1:3]), link
    return None, None

class Bundle:
    def __init__(self, url, name):
        self.name = name
        self.url = url
        self.gameGroups = {}

    def scrapeGames(self, isthereanydealapikey = None):
        soup = BeautifulSoup(urllib.request.urlopen(self.url), "lxml")

        groups = soup.findAll("div", "main-content-row dd-game-row js-nav-row")
        for g in groups:
            price = g.findAll("h2", "dd-header-headline")[0].text.strip()
            gnames = [d.text.strip() for d in g.findAll("div", "dd-image-box-caption dd-image-box-text dd-image-box-white ")]
            games = []
            for name in gnames:
                gid, link = query_steam_for_game(name)
                if gid != None:
                    newGame = Game(gid, 0, 0, 0, link, name, None)
                    if isthereanydealapikey is not None:
                        newGame.deal = isthedeal_wrapper.get_steam_price(isthereanydealapikey, gid)
                        if newGame.deal is not None:
                            newGame.cut = newGame.deal.current.cut
                            newGame.price = newGame.deal.current.price
                            if newGame.cut <= 0:
                                newGame.original_price = newGame.price
                            else:
                                newGame.original_price = newGame.price * 100 / newGame.cut
                    games.append(newGame)
                else:
                    games.append(Game("", 0, 0, 0, "", name, None))
            self.gameGroups[price] = games

    def __str__(self):
        ret = "{}\n{}\n".format(self.name, self.url)
        for g in self.gameGroups.keys():
            ret += "{}:\n".format(g)
            for game in self.gameGroups[g]:
                if game.gid is None or len(game.gid) <= 0:
                    ret += "\t{} (Not fonund on Steam Store)".format(game.name)
                else:
                    ret += "\t{}\n".format(game)
        return ret


def get_active_game_bundles(isthereanydealapikey = None):
    json = isthedeal_wrapper.require_json("https://hr-humblebundle.appspot.com/androidapp/v2/service_check")

    bundles = []
    if json is not None:
        for b in json:
            bundle = Bundle(b['url'], b['bundle_name'])
            bundle.scrapeGames(isthereanydealapikey)
            bundles.append(bundle)

    return bundles

if __name__ == '__main__':
    import os

    for b in get_active_game_bundles(os.environ["ISTHEREANYDEAL_API_KEY"]):
        print(b)

