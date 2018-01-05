import urllib3
import json
import logging

urllib3.disable_warnings()
http = urllib3.PoolManager()

regions = {}

__multiple_api_limit = 25

class PriceDeal:
    def __init__(self, shop, region, price, cut):
        self.shop = shop
        self.region = region
        self.price = price
        self.cut = cut

    @staticmethod
    def from_deal(deal_j, region):
        price = None
        if 'price_new' in deal_j:
            price = deal_j['price_new']
        elif 'price' in deal_j:
            price = deal_j['price']

        cut = None
        if 'price_cut' in deal_j:
            cut = deal_j['price_cut']
        elif 'cut' in deal_j:
            cut = deal_j['cut']

        return PriceDeal(deal_j['shop'], region, price, cut)

    def __str__(self):
        return "{}{} ({}%) on {}".format(self.price, self.region['currency'], self.cut, self.shop['name'])

    def to_dict(self):
        return {
            'shop': self.shop,
            'region': self.region,
            'price': self.price,
            'cut': self.cut
        }

    @staticmethod
    def from_dict(ddata):
        if ddata is None:
            return None
        return PriceDeal(ddata['shop'], ddata['region'], ddata['price'], ddata['cut'])


class Deal:
    def __init__(self, game_id, game_plain, current, historical, country):
        self.game_id = game_id
        self.game_plain = game_plain
        self.current_j = current
        self.historical_j = historical
        self.country = country
        region = get_region_by_country(country)
        if 'list' in current.keys() and len(current['list']) > 0:
                self.current = PriceDeal.from_deal(current['list'][0], region)
        else:
                self.current = None
        self.historical = PriceDeal.from_deal(historical, region)

    def __str__(self):
        return "{}: {}\nCurrent: {}\nHistorical: {}".format(self.game_id,
                                                            self.game_plain,
                                                            self.current,
                                                            self.historical)

    def to_dict(self):
        return {
            'game_id': self.game_id,
            'game_plain': self.game_plain,
            'current_j': self.current_j,
            'historical_j': self.historical_j,
            'country': self.country
        }

    @staticmethod
    def from_dict(ddata):
        if ddata is None:
            return None
        return Deal(ddata['game_id'], ddata['game_plain'], ddata['current_j'], ddata['historical_j'], ddata['country'])


def require_json(url):
    request = http.request('GET', url)
    if request.status == 200:
        return json.loads(request.data.decode('utf-8'))
    else:
        logging.error("bad request: {}".format(request.status))
        return None


def get_region_by_country(country):
    if country in regions:
        return regions[country]

    j = require_json('https://api.isthereanydeal.com/v01/web/regions/')
    region = None
    if j is not None:
        for r in j['data'].keys():
            if country in j['data'][r]['countries']:
                region = {'region': r, 'currency': j['data'][r]['currency']['sign']}
                break

    if region is not None:
        regions[country] = region
    else:
        logging.error("invalid country {}".format(country))
    return region


def get_game_plain_by_id(apy_key, game_id, shop='steam'):
    url = 'https://api.isthereanydeal.com/v02/game/plain/?key={}&shop={}&game_id={}'.format(apy_key, shop, game_id)

    j = require_json(url)
    if j is not None and 'plain' in j['data']:
        return j['data']['plain']
    else:
        logging.error("plain not found for game {}".format(game_id))
    return None


# returns a {game_id: game_plain} dictionary
def get_multiple_plain_by_ids(api_key, id_list, shop='steam'):
    if type(id_list) is str:
        id_list = id_list.split(',')
	
    out = {}
    while len(id_list) > 0:
        s_list = ",".join(id_list[:__multiple_api_limit])
        id_list = id_list[__multiple_api_limit:]
    
        url = 'https://api.isthereanydeal.com/v01/game/plain/id/?key={}&shop={}&ids={}'.format(api_key, shop, s_list)

        j = require_json(url)
        if j is not None:
            out.update(j['data'])
        else:
            logging.warning("no plain found for ids: {}".format(s_list))

    if len(out) > 0:
        return out
    return None


def __get_lowest(api_key, plains, country='IT'):
    region = get_region_by_country(country)['region']

    current_url = 'https://api.isthereanydeal.com/v01/game/prices/{}/?key={}&plains={}&country={}'.format(
        region, api_key, plains, country)
    historical_url = 'https://api.isthereanydeal.com/v01/game/lowest/{}/?key={}&plains={}'.format(
        region, api_key, plains)

    current_j = require_json(current_url)
    historical_j = require_json(historical_url)

    return current_j['data'], historical_j['data']


def get_game_lowest_prices(api_key, game_id, shop='steam', country='IT'):
    plain = get_game_plain_by_id(api_key, game_id, shop)
    if plain is None:
        return None

    cur_j, hist_j = __get_lowest(api_key, plain, country)

    return Deal(game_id, plain, cur_j[plain], hist_j[plain], country)


# returns a Deal list
def get_multiple_games_lowest_prices(api_key, id_list, shop='steam', country='IT'):
    plains_map = get_multiple_plain_by_ids(api_key, id_list, shop)
    if plains_map is None:
        return None

    plains_list = [p for p in plains_map.values()]

    dl = []
    while len(plains_list) > 0:
        p_list = ",".join(plains_list[:__multiple_api_limit])
        plains_list = plains_list[__multiple_api_limit:]

        cur_j, hist_j = __get_lowest(api_key, p_list, country)

        for gid in id_list:
            if gid in plains_map:
                pl = plains_map[gid]
                if pl in cur_j and pl in hist_j:
                    dl.append(Deal(gid, pl, cur_j[pl], hist_j[pl], country))
            else:
                logging.warning("gid {} was not resolved".format(gid))

    for i in id_list:
        found = False
        for d in dl:
            if d.game_id == i:
                found = True
                break
        if not found:
            if i in plains_map:
                logging.warning("{} ({}) not found".format(plains_map[i], i))
            else:
                logging.warning("{} not found".format(i))

    return dl
