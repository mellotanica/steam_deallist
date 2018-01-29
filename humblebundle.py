#!/usr/bin/env python3

import isthedeal_wrapper
import steam_deallist
import json
from bs4 import BeautifulSoup
import urllib.request
from userdata import Game
import datetime
import os


class Bundle:
    def __init__(self, url, name, id):
        self.name = name
        self.url = url
        self.id = id
        self.gameGroups = {}

    def scrapeGames(self, isthereanydealapikey = None):
        soup = BeautifulSoup(urllib.request.urlopen(self.url), "lxml")

        groups = soup.findAll("div", "main-content-row dd-game-row js-nav-row")
        for g in groups:
            price = g.findAll("h2", "dd-header-headline")[0].text.strip()
            gnames = [d.text.strip() for d in g.findAll("div", "dd-image-box-caption dd-image-box-text dd-image-box-white ")]
            games = []
            for name in gnames:
                gid, link = steam_deallist.query_steam_for_game(name)
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

    def to_dict(self):
        dict = {
            'name': self.name,
            'url': self.url,
            'id': self.id,
            'games': {}
        }
        for grp in self.gameGroups.keys():
            dict["games"][grp] = [g.to_dict() for g in self.gameGroups[grp]]
        return dict

    @staticmethod
    def from_dict(ddata):
        b = Bundle(ddata['url'], ddata['name'], ddata['id'])
        for grp in ddata['games'].keys():
            b.gameGroups[grp] = [Game.from_dict(d) for d in ddata['games'][grp]]
        return b


def get_active_game_bundles(isthereanydealapikey = None):
    json = isthedeal_wrapper.require_json("https://hr-humblebundle.appspot.com/androidapp/v2/service_check")

    bundles = []
    if json is not None:
        for b in json:
            bundle = Bundle(b['url'], b['bundle_name'], b['bundle_machine_name'])
            bundle.scrapeGames(isthereanydealapikey)
            bundles.append(bundle)

    return bundles


class BundleCache:
    def __init__(self, cache_path, isthereanydealapikey=None):
        if type(cache_path) is not str:
            raise Exception("Missing cache file")
        self.cache_path = cache_path
        self.isthereanydealapikey = isthereanydealapikey
        self.cache = None
        self.last_update = None
        self.already_notified = []
        self.available_bundles = []
        self.load()

    def load(self):
        if os.path.isfile(self.cache_path):
            f = open(self.cache_path, 'r')
            try:
                dict = json.load(f)
                if 'cache' in dict.keys() and 'update' in dict.keys():
                    self.last_update = datetime.date.fromordinal(dict['update'])
                    self.cache = [Bundle.from_dict(b) for b in dict['cache']]
                    self.already_notified = dict['notified']
            except:
                self.cache = None
            f.close()

        if self.cache is None or self.is_outdated():
            self.update()

    def update(self):
        self.cache = get_active_game_bundles(self.isthereanydealapikey)
        self.last_update = datetime.date.today()
        available = [b.id for b in self.cache]
        self.already_notified = list(set(self.already_notified) & set(available))

        self.store()

    def get_new_bundles(self):
        bundles = []
        for b in self.cache:
            if b.id not in self.already_notified:
                bundles.append(b)
        return bundles

    def notified_bundles(self, bundles):
        if type(bundles) is not list or len(bundles) <= 0:
            return
        for b in bundles:
            self.already_notified.append(b.id)
        self.store()

    def is_outdated(self):
        if self.last_update is None or self.last_update != datetime.date.today():
            return True
        return False

    def store(self):
        dict = {
            'update' : self.last_update.toordinal(),
            'cache' : [
                b.to_dict() for b in self.cache
            ],
            'notified': self.already_notified
        }
        if os.path.isfile(self.cache_path):
            mode = "w"
        else:
            mode = "x"

        f = open(self.cache_path, mode)
        json.dump(dict, f)
        f.close()

if __name__ == '__main__':
    for b in get_active_game_bundles(os.environ["ISTHEREANYDEAL_API_KEY"]):
        print(b)

