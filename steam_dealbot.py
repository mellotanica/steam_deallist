#!/usr/bin/env python3

from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup
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


custom_markup = [["Modify parameter"], ["Get results"], ["Cancel"]]

# interaction 0
def conv_custom_default(bot, update, user_data):
    global custom_markup

    message = "Min discount: {}%\nMax price: {}€\nMin discount for low price games: {}%\nWhat do you want to do?".format(user_data['discount'], user_data['price'], user_data['price_discount'])
    bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardMarkup(custom_markup), text=message)

    return 1

custom_set_markup = [["Price"], ["Low price Discount"], ["Discount"]]


# interaction 1
def conv_custom_default_answer(bot, update, user_data):
    global custom_markup
    global custom_set_markup

    if update.message.text == "Modify parameter":
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardMarkup(custom_set_markup), text="Which parameter do you want to set?")
        user_data['current_param'] = None
        return 2
    elif update.message.text == "Get results":
        return conv_custom_perform(bot, update, user_data)
    elif update.message.text == "Cancel":
        return conv_cancel(bot, update)

    bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardMarkup(custom_markup), text="Unknown choiche, what do you want to do?")
    return 1

# interaction 2
def conv_custom_set(bot, update, user_data):
    global custom_set_markup
    
    current_val = None
    ret = 3

    if update.message.text == "Price":
        current_val = str(user_data['price'])+"€"
        user_data['current_param'] = 'price'
    elif update.message.text == "Low price Discount":
        current_val = str(user_data['price_discount'])+"%"
        user_data['current_param'] = 'price_discount'
    elif update.message.text == "Discount":
        current_val = str(user_data['discount'])+"%"
        user_data['current_param'] = 'discount'
    else:
        ret = 2

    if current_val is None:
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardMarkup(custom_set_markup), text="Unknown choiche, what do you want to modify?")
    else:
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardRemove(), text="Current value: {}, specify new value".format(current_val))
    return ret

# interaction 3
def conv_custom_apply(bot, update, user_data):
    val = None

    try:
        val = float(update.message.text.replace(",", "."))
        if user_data['current_param'] != 'price':
            val = int(val)
    except:
        val = None

    if val is None:
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardRemove(), text="Unknown value, specify new value")
        return 3

    user_data[user_data['current_param']] = val

    return conv_custom_default(bot, update, user_data)

# interaction 4
def conv_custom_perform(bot, update, user_data):
    bot.send_message(chat_id=dest_id, reply_markup=ReplyKeyboardRemove(), text="Searching for deals...")
    send_deals(bot, steam_deallist.get_discount_games(max_price=user_data['price'], low_price_discount=user_data['price_discount'], min_discount=user_data['discount']))
    return ConversationHandler.END

def conv_cancel(bot, update):
    update.message.reply_text('Operation canceled', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def conv_custom_start(bot, update, user_data):
    if update.message.chat_id == dest_id:
        
        user_data['price'] = float(os.environ[steam_deallist.env_vars['price_threshold']].replace(",", "."))
        user_data['price_discount'] = int(float(os.environ[steam_deallist.env_vars['low_price_discount_threshold']].replace(",", ".")))
        user_data['discount'] = int(float(os.environ[steam_deallist.env_vars['discount_threshold']].replace(",", ".")))

        return conv_custom_default(bot, update, user_data)

#register telegram callbacks

dispatcher.add_handler(CommandHandler("deals", comm_deals))
dispatcher.add_handler(CommandHandler("stats", comm_stats))

dispatcher.add_handler(ConversationHandler(entry_points=[CommandHandler("custom", conv_custom_start, pass_user_data=True)], fallbacks=[CommandHandler("cancel", conv_cancel)], states={
        0: [MessageHandler(Filters.text, conv_custom_default, pass_user_data=True)],
        1: [MessageHandler(Filters.text, conv_custom_default_answer, pass_user_data=True)],
        2: [MessageHandler(Filters.text, conv_custom_set, pass_user_data=True)],
        3: [MessageHandler(Filters.text, conv_custom_apply, pass_user_data=True)],
        4: [MessageHandler(Filters.text, conv_custom_perform, pass_user_data=True)]
    }))

if update_time is not None:
    updater.job_queue.run_daily(job_deals, update_time)

print("telegram bot initialized, responding to user id {}".format(dest_id))
if update_time is not None:
    print("will send updates each day at {}".format(update_time))

# #run telegram bot

print("starting telegram bot")

updater.start_polling()
