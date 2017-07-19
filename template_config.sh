# telegram bot api key, to get one see: https://telegram.me/botfather
export STEAM_TELEGRAM_API_KEY="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# telegram user id to send the notifications to (only user allowed to contact the bot)
# to get your telegram user id see: https://telegram.me/userinfobot
export STEAM_TELEGRAM_USER_ID="XXXXXXXX"

# steam user whose wishlist is to be watched
export STEAM_USER="XXXXXXXX"

# min acceptable discount regardless of discount price for notifing a deal
export STEAM_MIN_DISCOUNT=XX

# max acceptable (discount) price for notifing a deal
export STEAM_MAX_PRICE=XX

# min acceptable discount for items with original price below `steam_max_price`
export STEAM_LOW_PRICE_DISCOUNT=XX

# auto updates time of day (set to -1 to disable automatic updates)
export STEAM_UPDATES_HOUR=XX
export STEAM_UPDATES_MINUTE=XX
