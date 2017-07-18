#!/usr/bin/env python3

from telegram.ext import Updater, CommandHandler
import logging
import os, sys
import steam_deallist
import datetime



env_vars = {
    'telegram_token'    : "STEAM_TELEGRAM_API_KEY",
    'user_id'           : "STEAM_TELEGRAM_USER_ID",
    'update_h'          : "STEAM_UPDATES_HOUR",
    'update_m'          : "STEAM_UPDATES_MINUTE"
}

#init apis
for var in env_vars.values():
    if var not in os.environ:
        print(var+" environment variable missing!\nplease run bot using start_bot.sh")
        exit(1)

if len(sys.argv) != 2:
    print("wrong arguments\nplease run bot using start_bot.sh")
    exit(1)

exclude_file = sys.argv[1]

if not os.path.isfile(exclude_file):
    print("{} is not a valid file\nplease run bot using start_bot.sh")
    exit(1)

telegram_token = os.environ[env_vars['telegram_token']]
dest_id = int(os.environ[env_vars['user_id']])
update_h = int(os.environ[env_vars['update_h']])
update_m = int(os.environ[env_vars['update_m']])

update_time = None
if update_h >= 0 and update_h < 24 and update_m >= 0 and update_m < 60:
    update_time = datetime.time(update_h, update_m)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

print("logger initialized")

updater = Updater(token=telegram_token)
dispatcher = updater.dispatcher

def send_deals(bot, games):
    if games is None or len(games) <= 0:
        bot.send_message(chat_id=dest_id, text="No deals available right now")
    else:
        for g in games:
            bot.send_message(chat_id=dest_id, text=steam_deallist.format_game_info(g))

def comm_deals(bot, update):
    if update.message.chat_id == dest_id:
        print("serving deals request")
        bot.send_message(chat_id=dest_id, text="Searching for deals...")
        send_deals(bot, steam_deallist.get_discount_games())

def job_deals(bot, job):
    excludes = None
    if os.path.isfile(exclude_file):
        ef = open(exclude_file, 'r')
        exclude_lines = ef.readlines()
        ef.close()
        excludes = []
        for e in exclude_lines:
            excludes.append(e[:-1])
    games = steam_deallist.get_discount_games(excludes)

    if excludes is None:
        om = 'x'
        excludes = []
    else:
        om = 'w'

    print("daily update start, excluded games: {}, got {} new deals".format(len(excludes), len(games)))
    if games is not None:
        if len(games) > 0:
            send_deals(bot, games)

    excludes = []
    all_games = steam_deallist.get_discount_games()
    for g in all_games:
        excludes.append(g['gameid']+"\n")

    print("updating excluded games, total excluded ids: {}".format(len(excludes)))

    ef = open(exclude_file, om)
    ef.writelines(excludes)
    ef.close()

    print("daily update done")

def comm_stats(bot, update):
    if update.message.chat_id == dest_id:
        stats = "bot status:\n" + steam_deallist.get_stats()
        stats += "\n"
        if update_time is None:
            stats += "no auto updates"
        else:
            stats += "update time = {}".format(update_time)
        print("stats:\n"+stats)
        bot.send_message(chat_id=dest_id, text=stats)

#register telegram callbacks

dispatcher.add_handler(CommandHandler("deals", comm_deals))
dispatcher.add_handler(CommandHandler("stats", comm_stats))

if update_time is not None:
    updater.job_queue.run_daily(job_deals, update_time)

print("telegram bot initialized, responding to user id {}".format(dest_id))
if update_time is not None:
    print("will send updates each day at {}".format(update_time))

# #run telegram bot

print("starting telegram bot")

updater.start_polling()
