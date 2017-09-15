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


