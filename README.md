# Steam Deallist Bot
Find best deals in personal wishlist and get notified right into telegram.

This bot will keep an eye for you on which games satisfy your discount needs throughout your wishlist and optionally notify each day about new deals.
You can also run custom queries on current deals list.

The wishlist scraper is provided as a library allowing for custom use cases

Additional market information is provided by [IsThereAnyDeal](https://isthereanydeal.com/).

# Requirements
To run the bot or the scraper you will need Python3 (>= 3.4), also the following python libraries:

- [beautyfulsoup4](https://www.crummy.com/software/BeautifulSoup/)
- [lxml](http://lxml.de/)
- [python-telegram-bot](https://python-telegram-bot.org/)

If you installed python-pip you can get the needed packages running
`pip3 install -r requirements.txt`
from inside the repository directory.


# Installation
Clone the repository

`git clone https://github.com/mellotanica/steam_deallist.git`

Install requirements

`pip3 install -r requirements.txt`

Run the bot

`./start_bot.sh`

The last command will ask you to fill in the needed configurations in the config file using the default editor.
If you want to use another editor to modify the configurations file, you can find it in `~/.config/steam_dealbot/steam_dealbot_config.sh`.


# steam_deallist library
The library needs one environment variable to be set to work properly:
- `STEAM_USER`: your steam username

You can also set default values by setting the following environment variables:
- `STEAM_MAX_PRICE`: max allowed price for a game to be appended to results list
- `STEAM_LOW_PRICE_DISCOUNT`: min discount percentage for games with staring price below `STEAM_MAX_PRICE`
- `STEAM_MIN_DISCOUNT`: min allowed discount percentage for a game to be appended to results list

The main function available to the user is:

`def get_discount_games(exclude=None, max_price=None, low_price_discount=None, min_discount=None, in_file=None, out_file=None)`

If run without parameters the call will use default values read from environment and return a list of game maps, the arguments have the following meaning:
- `exclude`: a list of game ids to be excluded from the results list
- `max_price`: same as `STEAM_MAX_PRICE`
- `low_price_discount`: same as `STEAM_LOW_PRICE_DISCOUNT`
- `min_discount`: same as `STEAM_MIN_DISCOUNT`
- `in_file`: cache file to read from, if this is Null, the actual wishlist from steam webpage is scraped; if a valid file is passed, the results are queried from the file
- `out_file`: file onto which the updated cache has to be written (if if_file is a valid cache file, its contents will be written to out_file). The cache will contain all disount games, ignoring query parameters.

The game map has the following keys:
- `'gameid'(str)`: the game id as steam knows it
- `'originalPrice'(float)`: the starting price without any discount applied
- `'finalPrice'(float)`: the current price of the game with discount applied
- `'discount'(int)`: the percentage amount
- `'name'(str)`: the name of the game as shown on steam wishlist
- `'link'(str)`: a link to the game store page

Other two service functions are provided:
- `def format_game_info(game)`: takes a game map and returns a formatted string describing the game and it's discount state
- `def print_game_list(games)`: takes a game map list and prints all its contents in a human readable way
