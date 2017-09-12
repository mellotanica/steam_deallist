#!/usr/bin/env python3

import os, re
from bs4 import BeautifulSoup
import urllib.request
import json
from isthedeal_wrapper import Deal, get_multiple_games_lowest_prices
from userdata import UserData, Game

optional_vars = {
    'isthereanydeal_api_key': 'ISTHEREANYDEAL_API_KEY'
}


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
        wish_games = soup.findAll("div", "wishlistRowItem")

	discount_games = {}

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

    	if optional_vars['isthereanydeal_api_key'] in os.environ:
		id_list = [g.gid for g in discount_games.values()]

		deals = get_multiple_games_lowest_prices(os.environ[optional_vars['isthereanydeal_api_key']], id_list)

		for d in deals:
			if d.game_id in discount_games:
				discount_games[d.game_id].deal = d

	return discount_games


def get_discount_games(user_data, max_price=None, low_price_discount=None, min_discount=None):
	if type(user_data) is not UserData:
		raise Exception("user_data must be a valid UserData object")

	if max_price is None:
		max_price = user_data.configs.max_price

	if low_price_discount is None:
		low_price_discount = user_data.configs.low_price_min_discount
	
	if min_discount is None:
		min_discount = user_data.configs.min_discount

    	if exclude is None:
        	exclude = []

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


def get_stats(user_data):
	user = user_data.username
	max_price = user_data.configs.max_price
	low_price_discount = user_data.configs.low_price_min_discount
	min_discount = user_data.configs.min_discount
	in_file_stat = "\nlocal cached games = {}".format(len(user_data.cache))

	return "user = {}\nmax_price = {}\nlow_price_discount = {}\nmin_discount = {}{}".format(user, max_price, low_price_discount, min_discount, in_file_stat)


if __name__ == '__main__':
	print_game_list(get_discount_games())
