import urllib3, json

urllib3.disable_warnings()
http = urllib3.PoolManager()

regions = {}

class PriceDeal:
    def __init__(self, shop, region, price, cut):
        self.shop = shop
        self.region = region
        self.price = price
        self.cut = cut

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

    def from_dict(ddata):
        return PriceDeal(ddata['shop'], ddata['region'], ddata['price'], ddata['cut'])

    def to_json(self):
        return json.dumps(self.to_dict())

    def from_json(jdata):
        if jdata is None:
            return None
        return PriceDeal.from_dict(json.loads(jdata))


class Deal:
    def __init__(self, game_id, game_plain, current, historical, country):
        self.game_id = game_id
        self.game_plain = game_plain
        self.current_j = current
        self.historical_j = historical
        self.country = country
        region = get_region_by_country(country)
        self.current = PriceDeal.from_deal(current['list'][0], region)
        self.historical = PriceDeal.from_deal(historical, region)

    def __str__(self):
        return "{}: {}\nCurrent: {}\nHistorical: {}".format(self.game_id, self.game_plain, self.current, self.historical)

    def to_dict(self):
        return {
            'game_id': self.game_id,
            'game_plain': self.game_plain,
            'current_j': self.current_j,
            'historical_j': self.historical_j,
            'country': self.country
        }

    def from_dict(ddata):
        return Deal(ddata['game_id'], ddata['game_plain'], ddata['current_j'], ddata['historical_j'], ddata['country'])

    def to_json(self):
        return json.dumps(self.to_dict())

    def from_json(jdata):
        if jdata is None:
            return None
        return Deal.from_dict(json.loads(jdata))


def require_json(url):
    request = http.request('GET', url)
    if request.status == 200:
        return json.loads(request.data.decode('utf-8'))
    else:
        print("bad request: {}".format(request.status))
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
        print("invalid country {}".format(country))
    return region


def get_game_plain_by_id(apy_key, game_id, shop='steam'):
    url = 'https://api.isthereanydeal.com/v02/game/plain/?key={}&shop={}&game_id={}'.format(apy_key, shop, game_id)

    j = require_json(url)
    if j is not None and 'plain' in j['data']:
        return j['data']['plain']
    else:
        print("plain not found for game {}".format(game_id))
    return None


# returns a {game_id: game_plain} dictionary
def get_multiple_plain_by_ids(api_key, id_list, shop='steam'):
    if type(id_list) is list:
        id_list = ",".join(id_list)
    url = 'https://api.isthereanydeal.com/v01/game/plain/id/?key={}&shop={}&ids={}'.format(api_key, shop, id_list)

    j = require_json(url)
    if j is not None:
        return j['data']
    else:
        print("no plain found for game id list: {}".format(id_list))
    return None


def __get_lowest(api_key, plains, shop='steam', country='IT'):
    region = get_region_by_country(country)['region']

    current_url = 'https://api.isthereanydeal.com/v01/game/prices/{}/?key={}&plains={}&country={}'.format(region, api_key, plains, country)
    historical_url = 'https://api.isthereanydeal.com/v01/game/lowest/{}/?key={}&plains={}'.format(region, api_key, plains)

    current_j = require_json(current_url)
    historical_j = require_json(historical_url)

    return (current_j['data'], historical_j['data'])


def get_game_lowest_prices(api_key, game_id, shop='steam', country='IT'):
    plain = get_game_plain_by_id(api_key, game_id, shop)
    if plain is None:
        return None

    cur_j, hist_j = __get_lowest(api_key, plain, shop, country)

    return Deal(game_id, plain, cur_j[plain], hist_j[plain], country)

#returns a Deal list
def get_multiple_games_lowest_prices(api_key, id_list, shop='steam', country='IT'):
    plains_map = get_multiple_plain_by_ids(api_key, id_list, shop)
    if plains_map is None:
        return None

    plains_list = ",".join(plains_map.values())

    cur_j, hist_j = __get_lowest(api_key, plains_list, shop, country)

    dl = []
    for id in id_list:
        if id in plains_map:
            pl = plains_map[id]
            if pl in cur_j and pl in hist_j:
                dl.append(Deal(id, pl, cur_j[pl], hist_j[pl], country))
    return dl

