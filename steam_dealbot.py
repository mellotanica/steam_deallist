#!/usr/bin/env python3

from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup
import logging
import os
import sys
import steam_deallist
import datetime

from userdata import UserDataManager

env_vars = {
    'telegram_token': "STEAM_TELEGRAM_API_KEY",
    'update_h': "STEAM_UPDATES_HOUR",
    'update_m': "STEAM_UPDATES_MINUTE"
}

# init apis
for var in env_vars.values():
    if var not in os.environ:
        print(var + " environment variable missing!\nplease run bot using start_bot.sh")
        exit(1)

if len(sys.argv) != 2:
    print("wrong arguments\nplease run bot using start_bot.sh")
    exit(1)

cache_dir = sys.argv[1]
user_data_manager = UserDataManager(cache_dir)

# if not os.path.isfile(exclude_file):
# 	print("{} is not a valid file\nplease run bot using start_bot.sh".format(exclude_file))
# 	exit(1)

telegram_token = os.environ[env_vars['telegram_token']]
update_h = int(os.environ[env_vars['update_h']])
update_m = int(os.environ[env_vars['update_m']])

update_time = None
if 0 <= update_h < 24 and 0 <= update_m < 60:
    update_time = datetime.time(update_h, update_m)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)

print("logger initialized")

updater = Updater(token=telegram_token)
dispatcher = updater.dispatcher


def send_deals(bot, tid, games):
    if games is None or len(games) <= 0:
        bot.send_message(chat_id=tid, text="No deals available right now")
    else:
        for g in games:
            bot.send_message(chat_id=tid, text=str(g))


def comm_deals(bot, update):
    global user_data_manager
    user_data = user_data_manager.get_userdata(update.message.chat_id)

    if user_data is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return

    send_deals(bot, user_data.tid, steam_deallist.get_discount_games(user_data))


def job_deals(bot, job):
    global cache_dir, user_data_manager

    print("updating local caches")

    for f in os.scandir(cache_dir):
        if f.is_file():
            try:
                tid = int(f.name)
            except:
                tid = None
            if tid is not None:
                ud = user_data_manager.get_userdata(tid)
                if ud is not None:
                    print("updating cache for tid {}, user {}".format(ud.tid, ud.username))

                    ud.cache = steam_deallist.get_updated_user_cache(ud)

                    games = steam_deallist.get_discount_games(ud, ignore_excludes=False)
                    if len(games) > 0:
                        send_deals(bot, ud.tid, games)

                    ud.set_exclude_cache()
                    user_data_manager.store_userdata(ud)

    print("daily update done")


def comm_stats(bot, update):
    global user_data_manager
    user_data = user_data_manager.get_userdata(update.message.chat_id)

    if user_data is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return

    stats = "bot status:\n" + steam_deallist.get_stats(user_data)
    print("stats:\n" + stats)
    bot.send_message(chat_id=update.message.chat_id, text=stats)


def comm_update(bot, update, user_data=None):
    global user_data_manager
    if user_data is None:
        user_data = user_data_manager.get_userdata(update.message.chat_id)

    if user_data is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return

    update_message = bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardRemove(),
                                      text="Updating local cache...")
    print("updating user data cache (size: {})...".format(len(user_data.cache)))
    user_data.cache = steam_deallist.get_updated_user_cache(user_data)
    print("updated, new size: {}".format(len(user_data.cache)))
    user_data_manager.store_userdata(user_data)
    print("user data stored, modifiyng message")
    bot.edit_message_text("Local cache updated", chat_id=update.message.chat_id, message_id=update_message.message_id)
    return update_message


# start conversation

def conv_start_start(bot, update, user_data):
    global user_data_manager
    ud = user_data_manager.get_userdata(update.message.chat_id)

    text = "Hi, i can track your steam wishlist and alert you when game you want is on sale with a new juicy deal\n"
    ret = ConversationHandler.END
    if ud is None:
        text += "First of all tell me your steam account id (i.e. your username) " \
                "and make sure your steam wishlist is public"
        ret = 0
        ud = user_data_manager.init_userdata(update.message.chat_id)
    else:
        text += "I will notify you every day if a new deal is released, " \
                "you can also ask me to perform custom queries on your wishlist " \
                "deals with /custom command, list all your applicable /deals, " \
                "/update deals information, change /settings or show you some /stats. " \
                "(Remember that your steam wishlist must be public for me to read it!)"

    user_data['ud'] = ud
    bot.send_message(chat_id=update.message.chat_id, text=text)
    return ret


def conv_start_username(bot, update, user_data):
    user_data['ud'].username = update.message.text

    bot.send_message(chat_id=update.message.chat_id,
                     text="Are you sure? is \"{}\" correct?".format(update.message.text),
                     reply_markup=ReplyKeyboardMarkup([["Yes"], ["No"]]))

    return 1


def conv_start_confirm(bot, update, user_data):
    global user_data_manager
    repl = update.message.text.lower()

    if repl in 'yes':
        ud = user_data['ud']
        text = "All right {}, I will notify you every day if a new deal is released, " \
               "you can also ask me to perform custom queries on your wishlist deals " \
               "with /custom command, list all your applicable /deals, /update deals " \
               "information, change /settings or show you some /stats".format(ud.username)
        um = comm_update(bot, update, ud)
        bot.edit_message_text(text, chat_id=update.message.chat_id, message_id=um.message_id)
        user_data_manager.store_userdata(ud)
        return ConversationHandler.END
    elif repl in 'no':
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardRemove(),
                         text="Ok, so what's your steam username again?")
        return 0
    bot.send_message(chat_id=update.message.chat_id, text="I didn't understand, "
                                                          "are you sure? (Yes/No)")
    return 1


# settings conversation

# custom conversation
custom_markup = [["Modify parameter"], ["Get results"], ["Cancel"]]


# interaction 0
def conv_custom_default(bot, update, user_data, message=""):
    global custom_markup

    message += "Min discount: {}%\nMax price: {}€\nMin discount for low price games: {}%\n" \
               "What do you want to do?".format(user_data['discount'], user_data['price'], user_data['price_discount'])
    bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardMarkup(custom_markup), text=message)

    return 1


custom_set_markup = [["Price"], ["Low price Discount"], ["Discount"], ["Cancel"]]


# interaction 1
def conv_custom_default_answer(bot, update, user_data):
    global custom_set_markup

    if update.message.text == "Modify parameter":
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardMarkup(custom_set_markup),
                         text="Which parameter do you want to set?")
        user_data['current_param'] = None
        return 2
    elif update.message.text == "Get results":
        return conv_custom_perform(bot, update, user_data)
    elif update.message.text == "Cancel":
        return conv_cancel(bot, update)

    return conv_custom_default(bot, update, user_data, "Unknown choice.\n\n")


# interaction 2
def conv_custom_set(bot, update, user_data):
    global custom_set_markup

    current_val = None
    ret = 3

    if update.message.text == "Price":
        current_val = str(user_data['price']) + "€"
        user_data['current_param'] = 'price'
    elif update.message.text == "Low price Discount":
        current_val = str(user_data['price_discount']) + "%"
        user_data['current_param'] = 'price_discount'
    elif update.message.text == "Discount":
        current_val = str(user_data['discount']) + "%"
        user_data['current_param'] = 'discount'
    elif update.message.text == "Cancel":
        return conv_custom_default(bot, update, user_data, "Operation caceled.\n\n")
    else:
        ret = 2

    if current_val is None:
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardMarkup(custom_set_markup),
                         text="Unknown choiche, what do you want to modify?")
    else:
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardMarkup([["Cancel"]]),
                         text="Current value: {}, specify new value".format(current_val))
    return ret


# interaction 3
def conv_custom_apply(bot, update, user_data):
    global custom_set_markup

    if update.message.text == "Cancel":
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardMarkup(custom_set_markup),
                         text="Which parameter do you want to set?")
        user_data['current_param'] = None
        return 2

    try:
        val = float(update.message.text.replace(",", "."))
        if user_data['current_param'] != 'price':
            val = int(val)
    except:
        val = None

    if val is None:
        bot.send_message(chat_id=update.message.chat_id, text="Unknown value, specify new value")
        return 3

    user_data[user_data['current_param']] = val

    return conv_custom_default(bot, update, user_data)


# interaction 4
def conv_custom_perform(bot, update, user_data):
    send_deals(bot,
               update.message.chat_id,
               steam_deallist.get_discount_games(
                   user_data['ud'], max_price=user_data['price'],
                   low_price_discount=user_data['price_discount'],
                   min_discount=user_data['discount']
               )
    )
    return ConversationHandler.END


def conv_cancel(bot, update):
    update.message.reply_text('Operation canceled', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def conv_custom_start(bot, update, user_data):
    global user_data_manager

    ud = user_data_manager.get_userdata(update.message.chat_id)
    if ud is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return ConversationHandler.END

    user_data['ud'] = ud
    user_data['price'] = ud.configs.max_price
    user_data['price_discount'] = ud.configs.low_price_min_discount
    user_data['discount'] = ud.configs.min_discount

    return conv_custom_default(bot, update, user_data)


# register telegram callbacks

dispatcher.add_handler(CommandHandler("deals", comm_deals))
dispatcher.add_handler(CommandHandler("stats", comm_stats))
dispatcher.add_handler(CommandHandler("update", comm_update))

dispatcher.add_handler(
    ConversationHandler(entry_points=[CommandHandler("start", conv_start_start, pass_user_data=True)],
                        fallbacks=[CommandHandler("cancel", conv_cancel)], states={
            0: [MessageHandler(Filters.text, conv_start_username, pass_user_data=True)],
            1: [MessageHandler(Filters.text, conv_start_confirm, pass_user_data=True)]
        }))

dispatcher.add_handler(
    ConversationHandler(entry_points=[CommandHandler("custom", conv_custom_start, pass_user_data=True)],
                        fallbacks=[CommandHandler("cancel", conv_cancel)], states={
            0: [MessageHandler(Filters.text, conv_custom_default, pass_user_data=True)],
            1: [MessageHandler(Filters.text, conv_custom_default_answer, pass_user_data=True)],
            2: [MessageHandler(Filters.text, conv_custom_set, pass_user_data=True)],
            3: [MessageHandler(Filters.text, conv_custom_apply, pass_user_data=True)],
            4: [MessageHandler(Filters.text, conv_custom_perform, pass_user_data=True)]
        }))

if update_time is not None:
    updater.job_queue.run_daily(job_deals, update_time)

print("telegram bot initialized")
if update_time is not None:
    print("will send updates each day at {}".format(update_time))

# #run telegram bot

print("starting telegram bot")

updater.start_polling()

updater.idle()