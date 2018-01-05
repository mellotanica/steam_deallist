import os
import json
from isthedeal_wrapper import Deal


# userdata:
# 	(steam)username
#   dault_user_configs
#   [exclude, ..]
#   cache: game list

# user_configs:
#   max_price
#   min_discount
#   min_discount_for_low_price

# exclude:
#   gameid
#   discount_price

class UserConfigs:
    def __init__(self, max_price, min_discount, low_price_min_discount):
        self.max_price = max_price
        self.min_discount = min_discount
        self.low_price_min_discount = low_price_min_discount

    def __str__(self):
        return "Max game price: {}, Minimum discount: {}%, Minimum discount for low price games: {}%".format(
            self.max_price, self.min_discount, self.low_price_min_discount
        )

    @staticmethod
    def get_default():
        return UserConfigs(5, 75, 50)

    def to_dict(self):
        return {
            'max_price': self.max_price,
            'min_discount': self.min_discount,
            'low_price_min_discount': self.low_price_min_discount
        }

    @staticmethod
    def from_dict(ddata):
        return UserConfigs(ddata['max_price'], ddata['min_discount'], ddata['low_price_min_discount'])


class Exclude:
    def __init__(self, gid, price):
        self.gid = gid
        self.price = price

    def to_dict(self):
        return {
            'game_id': self.gid,
            'price': self.price
        }

    @staticmethod
    def from_dict(ddata):
        return Exclude(ddata['game_id'], ddata['price'])


class Game:
    def __init__(self, gid, original_price, price, cut, link, name, deal):
        self.gid = gid
        self.original_price = original_price
        self.price = price
        self.cut = cut
        self.link = link
        self.name = name
        self.deal = deal

    def is_recommended(self):
        if type(self.deal) is Deal:
            if self.price <= self.deal.historical.price:
                return True
            if self.deal.current.price <= self.deal.historical.price:
                if self.deal.current.shop['id'] == 'steam':
                    return True
        return False

    def __str__(self):
        ret = "{}".format(self.name)
        ret += "\nprice: {}€ ({}€ - {}%)".format(self.price, self.original_price, self.cut)
        if self.deal is not None:
            if self.is_recommended():
                ret += "\n💰💸Best deal on the market, go buy it now!💸💰"
            elif self.deal.current.price >= self.deal.historical.price:
                ret += "\nLowest price: {}".format(self.deal.current)
            elif self.deal.current.shop['id'] == 'steam':
                ret += "\nHistorical lowest price: {}".format(self.deal.historical)
            else:
                ret += "\nLowest prices: current {}, all time {}".format(self.deal.current, self.deal.historical)
        ret += "\nStore page: {}".format(self.link)
        return ret

    def is_applicable(self, max_price, low_price_discount, min_discount, exclude, include_recommended=False):
        if self.gid not in exclude.keys() or self.price != exclude[self.gid]:
            if self.price <= max_price:
                if self.original_price <= max_price:
                    if self.cut >= low_price_discount:
                        return True
                else:
                    return True
            elif self.cut >= min_discount:
                return True
            elif include_recommended and self.is_recommended():
                return True
        return False

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

    @staticmethod
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


class UserData:
    def __init__(self, tid, username, configs, exclude_list=None, cache=None):
        self.tid = tid
        self.username = username
        self.configs = configs
        if exclude_list is None:
            self.exclude_list = []
        else:
            self.exclude_list = exclude_list
        if cache is None:
            self.cache = []
        else:
            self.cache = cache

    def __str__(self):
        ret = "Telegram id: {}, Steam username: {}".format(self.tid, self.username)
        ret += "\nconfigs: {}".format(self.configs)
        cs = 0
        if self.cache is not None:
            cs = len(self.cache)
        ret += "\nGames cached: {}".format(cs)
        if self.exclude_list is not None and len(self.exclude_list) > 0:
            ret += "\nExcluded game ids: {}".format(", ".join([x.gid for x in self.exclude_list]))
        else:
            ret += "\nNo game excluded yet"
        return ret

    @staticmethod
    def get_default(tid):
        return UserData(tid, "gabelogannewell", UserConfigs.get_default())

    def get_exclude_map(self):
        return {x.gid: x.price for x in self.exclude_list}

    def set_exclude_cache(self):
        self.exclude_list = [Exclude(g.gid, g.price) for g in self.cache]

    def to_dict(self):
        return {
            'telegram_id': self.tid,
            'username': self.username,
            'configs': self.configs.to_dict(),
            'exclude_list': [x.to_dict() for x in self.exclude_list],
            'cache': [g.to_dict() for g in self.cache]
        }

    @staticmethod
    def from_dict(ddata):
        return UserData(
            ddata['telegram_id'],
            ddata['username'],
            UserConfigs.from_dict(ddata['configs']),
            [Exclude.from_dict(x) for x in ddata['exclude_list']],
            [Game.from_dict(g) for g in ddata['cache']]
        )


class UserDataManager:
    def __init__(self, cache_path):
        if type(cache_path) is not str or not os.path.isdir(cache_path):
            raise Exception("Missing cache path")
        self.cache_path = cache_path

    # reads userdata, if user is unknown initializes a new userdata
    def get_userdata(self, tid):
        if type(tid) is not int:
            raise Exception("Telegram id needs to be a valid int, found type {}".format(type(tid)))

        fpath = self.cache_path + "/" + str(tid)

        if os.path.isfile(fpath):
            f = open(fpath, 'r')
            try:
                d = UserData.from_dict(json.load(f))
            except:
                d = None
            f.close()
            return d
        return None

    @staticmethod
    def init_userdata(tid):
        if type(tid) is not int:
            raise Exception("Telegram id needs to be a valid int, found type {}".format(type(tid)))

        return UserData.get_default(tid)

    def store_userdata(self, user_data):
        if type(user_data) is not UserData:
            raise Exception("user_data must be a UserData object")

        fpath = self.cache_path + "/" + str(user_data.tid)

        if os.path.isfile(fpath):
            mode = "w"
        else:
            mode = "x"

        f = open(fpath, mode)
        json.dump(user_data.to_dict(), f)
        f.close()
