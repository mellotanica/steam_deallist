import os, json

# userdata:
# 	(steam)username
#	dault_user_configs
#	[exclude, ..]
#	cache: game list

# user_configs:
#	max_price
#	min_discount
#	min_discount_for_low_price

# exclude:
#	gameid
#	discount_price

class UserConfigs:
	def __init__(self, max_price, min_discount, low_price_min_discount):
		self.max_price = max_price
		self.min_discount = min_discount
		self.low_price_min_discount = low_price_min_discount
	
	def get_default():
		return UserConfigs(5, 75, 50)

	def to_dict(self):
		return {
			'max_price' : self.max_price,
			'min_discount' : self.min_discount,
			'low_price_min_discount' : self.low_price_min_discount
		}
	
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



class UserData:
	def __init__(self, tid, username, configs, exclude_list=None, cache=None):
		self.tid = tid
		self.username = username
		self.configs = configs
		self.exclude_list = exclude_list
		self.cache = cache

	def get_default(tid):
		return UserData(tid, "gabelogannewell", UserConfigs.get_default())

	def to_dict(self):
		return {
			'telegram_id': self.tid
			'username': self.username,
			'configs': self.configs.to_dict(),
			'exclude_list': [x.to_dict() for x in self.exclude_list],
			'cache': [g.to_dict() for g in self.cache]
		}
	
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


	#reads userdata, if user is unknown initializes a new userdata
	def get_userdata(self, tid):
		if type(tid) is not str:
			raise Exception("Telegram id needs to be a valid string")

		fpath = self.cache_path + "/" + tid

		if os.path.is_file(fpath):
			f = open(fpath, 'r')
			d = UserData.from_dict(json.load(f))
			f.close()
			return d
		return None


	def init_userdata(self, tid):
		if type(tid) is not str:
			raise Exception("Telegram id needs to be a valid string")

		return UserData.get_default(tid)

	
	def store_userdata(self, user_data):
		if type(user_data) is not UserData:
			raise Exception("user_data must be a UserData object")

		fpath = self.cache_path + "/" + user_data.tid

		if os.path.isfile(fpath):
			mode = "w"
		else:
			mode = "x"

		f = open(fpath, mode)
		json.dump(user_data.to_to_dict(), f)
		f.close()

