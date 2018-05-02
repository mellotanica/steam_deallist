#!/usr/bin/env python3

env_vars = {
    'telegram_token': "STEAM_TELEGRAM_API_KEY",
    'update_h': "STEAM_UPDATES_HOUR",
    'update_m': "STEAM_UPDATES_MINUTE",
    'notification_file': "NOTIFICATION_FILE"
}

import sys
import os
import logging

# check needed env vars and arguments before declaring functions
for var in env_vars.values():
    if var not in os.environ:
        logging.critical(var + " environment variable missing!\nplease run bot using start_bot.sh")
        exit(1)

if len(sys.argv) != 2:
    logging.critical("wrong arguments\nplease run bot using start_bot.sh")
    exit(2)

cache_dir = sys.argv[1]
if not os.path.isdir(cache_dir):
    logging.critical("{} is not a valid directory\nplease run bot using start_bot.sh")
    exit(2)

bundle_cache_file = os.path.join(cache_dir, "bundles_cache")
tid_cache_dir = os.path.join(cache_dir, "tids")
if not os.path.isdir(tid_cache_dir):
    os.mkdir(tid_cache_dir)

from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, TelegramError, ParseMode
import steam_deallist
import datetime
from userdata import UserDataManager
from humblebundle import BundleCache

# #### MISC ####

def send_deals(bot, tid, games):
    try:
        if games is None or len(games) <= 0:
            bot.send_message(chat_id=tid, text="No deals available right now")
        else:
            for g in games:
                bot.send_message(chat_id=tid, parse_mode=ParseMode.HTML, text=g.to_string(True))
    except TelegramError as e:
        logging.error("error %s\nwhile sending games to %s", e, tid)


def send_bundles(bot, tid, bundles):
    try:
        for bundle in bundles:
            bot.send_message(chat_id=tid, parse_mode=ParseMode.HTML, text='<b>VVV</b> <a href="{}">{}</a> <b>VVV</b>'.format(bundle.url, bundle.name))
            for grp in bundle.gameGroups.keys():
                bot.send_message(chat_id=tid, parse_mode=ParseMode.HTML, text='<i>{}</i>'.format(grp))
                send_deals(bot, tid, bundle.gameGroups[grp])
            bot.send_message(chat_id=tid, parse_mode=ParseMode.HTML, text="<b>ΛΛΛ {} ΛΛΛ</b>".format(bundle.name))
    except TelegramError as e:
        logging.error("error %s\nwhile sending bundles to %s", e, tid)

# #### COMMANDS ####

def comm_deals(bot, update):
    global user_data_manager
    user_data = user_data_manager.get_userdata(update.message.chat_id)

    if user_data is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return

    try:
        send_deals(bot, user_data.tid, steam_deallist.get_discount_games(user_data))
    except TelegramError as e:
        logging.error(e)


def comm_stats(bot, update):
    global user_data_manager
    user_data = user_data_manager.get_userdata(update.message.chat_id)

    if user_data is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return

    stats = "bot status:\n" + steam_deallist.get_stats(user_data)
    bot.send_message(chat_id=update.message.chat_id, text=stats)


def comm_update(bot, update, user_data=None, send_message=True):
    global user_data_manager
    if user_data is None:
        user_data = user_data_manager.get_userdata(update.message.chat_id)

    if user_data is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return

    if send_message:
        update_message = bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardRemove(),
                                      text="Updating local cache...⏳")
    user_data.cache = steam_deallist.get_updated_user_cache(user_data)
    user_data_manager.store_userdata(user_data)
    if send_message:
        try:
            bot.edit_message_text(chat_id=update.message.chat_id, message_id=update_message.message_id, text="Local cache updated")
        except TelegramError as e:
            bot.send_message(chat_id=update.message.chat_id, text="Local cache updated")
            update_message = None
        return update_message


def comm_all_deals(bot, update):
    global user_data_manager
    user_data = user_data_manager.get_userdata(update.message.chat_id)

    if user_data is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return

    send_deals(bot, update.message.chat_id, user_data.cache)


def comm_bundles(bot, update):
    global bundles_cache
    global user_data_manager

    user_data = user_data_manager.get_userdata(update.message.chat_id)

    if user_data is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return

    send_bundles(bot, update.message.chat_id, bundles_cache.cache)

def comm_help(bot, update):
    global user_data_manager
    user_data = user_data_manager.get_userdata(update.message.chat_id)

    if user_data is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return

    text = "## Available commands ##\n" \
           "  - /deals \n" \
           "       get all deals that respect the active settings\n" \
           "  - /bundles \n" \
           "       get all active game bundles from HumbleBundle\n" \
           "  - /settings \n" \
           "       review and change settings (see below)\n" \
           "  - /custom \n" \
           "       perform a query on your wishlist with temporary settings\n" \
           "  - /alldeals \n" \
           "       list every game in your wishlist currently on sale\n" \
           "  - /help \n" \
           "       show this help text\n" \
           "  - /start \n" \
           "       show start message\n" \
           "  - /update \n" \
           "       trigger an update of the local cache\n" \
           "  - /stats \n" \
           "       show some statistics on your account\n" \
           "\n\n" \
           "## Settings ##\n" \
           "The current deal list is filtered applying two thresholds:\n" \
           "  - 'Max Price': maximum price accepted\n" \
           "  - 'Min Discount': minimum discount percentage accepted\n" \
           "Deals are filtered excluding games that don't respect both the two thresholds, " \
           "for the ones that have an original price that is already below the price " \
           "threshold, the 'Low Price Discount' threshold is checked against discount percentage.\n"

    bot.send_message(chat_id=update.message.chat_id, text=text)


# #### CONVERSATIONS ####

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
        text += "I will notify you every day if new deals are released, " \
                "you can also ask me to list all your applicable /deals (or /alldeals regardless of your settings)," \
                "perform custom queries on your wishlist deals with /custom command,  " \
                "/update deals information, change /settings or show you some /stats. " \
                "I can provide you more info if you aske me for /help. " \
                "(Remember that your steam wishlist must be public for me to read it!)" \
                "\n\nI am an open source bot, find me on https://github.com/mellotanica/steam_deallist"

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
        text = "All right {}, I will notify you every day if new deals are released, " \
               "you can also ask me to list all your applicable /deals (or /alldeals regardless of your settings)," \
               "perform custom queries on your wishlist deals with /custom command,  " \
               "/update deals information, change /settings or show you some /stats. " \
                "I can provide you more info if you aske me for /help. " \
                "\n\nI am an open source bot, find me on https://github.com/mellotanica/steam_deallist".format(ud.username)
        um = bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardRemove(),
                              text="Initializing cache..⏳")
        comm_update(bot, update, ud, False)
        try:
            bot.edit_message_text(text, chat_id=update.message.chat_id, message_id=um.message_id)
        except TelegramError as e:
            bot.send_message(text=text, chat_id=update.message.chat_id)

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
__settings_username = 0
__settings_max_price = 1
__settings_min_discount = 2
__settings_low_price_discount = 3
__settings_show_best_deals = 4
__settings_humble_bundle_enabled = 5


def conv_settings_default(bot, update, user_data, message = ""):
    ud = user_data['ud']

    markup = [['Min Discount', 'Max Price'], ['Low Price Discount', 'Show Best Deals'], ['Username', 'HumbleBundle Notifications'], ['Done']]

    message += "Steam Username: {}\nMin discount: {}%\nMax price: {}€\nMin discount for low price games: {}%\n" \
        "Show all best deals: {}\nHumbleBundle notifications: {}" \
        "What do you want to modify?".format(ud.username, ud.configs.min_discount, ud.configs.max_price,
            ud.configs.low_price_min_discount, ud.configs.show_best_deals, ud.configs.humble_bundle_enabled)
    bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardMarkup(markup), text=message)

    return 0


def conv_settings_start(bot, update, user_data):
    global user_data_manager

    ud = user_data_manager.get_userdata(update.message.chat_id)
    if ud is None:
        bot.send_message(chat_id=update.message.chat_id, text="Account not configured! Please, issue /start command")
        return

    user_data['ud'] = ud
    user_data['original_user'] = ud.username

    return conv_settings_default(bot, update, user_data)


def conv_settings_set(bot, update, user_data):
    global user_data_manager

    text = update.message.text.lower()

    current_val = None
    ret = 1

    if text in "max price":
        current_val = str(user_data['ud'].configs.max_price) + "€"
        user_data['current_param'] = __settings_max_price
    elif text in "low price discount":
        current_val = str(user_data['ud'].configs.low_price_min_discount) + "%"
        user_data['current_param'] = __settings_low_price_discount
    elif text in "min discount":
        current_val = str(user_data['ud'].configs.min_discount) + "%"
        user_data['current_param'] = __settings_min_discount
    elif text in 'username':
        current_val = user_data['ud'].username
        user_data['current_param'] = __settings_username
    elif text in 'show best deals':
        current_val = user_data['ud'].configs.show_best_deals
        user_data['current_param'] = __settings_show_best_deals
        ret = 2
    elif text in 'humblebundle notifications':
        current_val = user_data['ud'].configs.humble_bundle_enabled
        user_data['current_param'] = __settings_humble_bundle_enabled
        ret = 2
    elif text in "done" or text in "cancel":
        user_data_manager.store_userdata(user_data['ud'])
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardRemove(),
                         text="Settings modified.")
        if user_data['original_user'] != user_data['ud'].username:
            comm_update(bot, update, user_data['ud'])
        return ConversationHandler.END
    else:
        ret = 0

    if current_val is None:
        bot.send_message(chat_id=update.message.chat_id, text="Unknown choice, what do you want to modify?")
    elif ret == 2:
        text = "Current value: "
        if current_val:
            text += "enabled"
        else:
            text += "disabled"
        text += ", specify new value"
        bot.send_message(chat_id=update.message.chat_id, text=text, reply_markup=ReplyKeyboardMarkup([["Enable"], ['Disable']]))
    else:
        bot.send_message(chat_id=update.message.chat_id, reply_markup=ReplyKeyboardRemove(),
                         text="Current value: {}, specify new value".format(current_val))
    return ret


def conv_settings_apply(bot, update, user_data):
    if update.message.text.lower() in "cancel":
        user_data['current_param'] = None
        return conv_settings_default(bot, update, user_data)

    param = user_data['current_param']
    if param != __settings_username:
        try:
            val = float(update.message.text.replace(",", "."))
            if param != __settings_max_price:
                val = int(val)
        except:
            val = None
    else:
        val = update.message.text

    if val is None:
        bot.send_message(chat_id=update.message.chat_id, text="Unknown value, specify new value")
        return 1

    if param == __settings_max_price:
        user_data['ud'].configs.max_price = val
    elif param == __settings_low_price_discount:
        user_data['ud'].configs.low_price_min_discount = val
    elif param == __settings_min_discount:
        user_data['ud'].configs.min_discount = val
    elif param == __settings_username:
        user_data['ud'].username = val

    return conv_settings_default(bot, update, user_data)


def conv_settings_boolean(bot, update, user_data):
    if update.message.text.lower() in "cancel":
        user_data['current_param'] = None
        return conv_settings_default(bot, update, user_data)

    val = update.message.text.lower()
    if val in 'enable':
        val = True
    elif val in 'disable':
        val = False
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Unknown value, specify new value")
        return 2

    param = user_data['current_param']
    if param == __settings_show_best_deals:
        user_data['ud'].configs.show_best_deals = val
    elif param == __settings_humble_bundle_enabled:
        user_data['ud'].configs.humble_bundle_enabled = val

    return conv_settings_default(bot, update, user_data)



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


def conv_cancel(bot, update):
    update.message.reply_text('Operation canceled', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# #### JOBS ####

def job_deals(bot, job):
    global user_data_manager

    logging.info("updating local caches")

    for tid in user_data_manager.get_userlist():
        ud = user_data_manager.get_userdata(tid)
        if ud is not None:
            logging.info("updating cache for tid {}, user {}".format(ud.tid, ud.username))

            ud.cache = steam_deallist.get_updated_user_cache(ud)

            games = steam_deallist.get_discount_games(ud, ignore_excludes=False)
            if len(games) > 0:
                send_deals(bot, ud.tid, games)

            ud.set_exclude_cache()
            user_data_manager.store_userdata(ud)

    logging.info("daily update done")


def job_bundles(bot, job):
    global bundle_cache_file, bundles_cache, user_data_manager

    if bundles_cache is None or bundles_cache.is_outdated():
        logging.info("updating bundles cache")

        if bundles_cache is None:
            bundles_cache = BundleCache(bundle_cache_file, os.environ[steam_deallist.optional_vars['isthereanydeal_api_key']])
        else:
            bundles_cache.update()

        notified = []
        for bundle in bundles_cache.get_new_bundles():
            notified.append(bundle)

        for tid in user_data_manager.get_userlist():
            ud = user_data_manager.get_userdata(tid)
            if ud is not None and ud.configs.humble_bundle_enabled:
                send_bundles(bot, tid, notified)

        bundles_cache.notified_bundles(notified)

        logging.info("bundles cache updated")

def job_sporadic_notify(bot, job):
    global user_data_manager, env_vars

    if env_vars['notification_file'] in os.environ:
        if os.path.exists(os.environ[env_vars['notification_file']]):
            logging.info("found notification file")
            f = open(os.environ[env_vars['notification_file']], 'r')
            content = f.read()
            f.close()
            os.rename(os.environ[env_vars['notification_file']], os.environ[env_vars['notification_file']]+"_done")
            if content is not None and len(content) > 0:
                logging.info("notifying message:\n{}".format(content))
                for tid in user_data_manager.get_userlist():
                    bot.send_message(chat_id=tid, parse_mode=ParseMode.HTML, text=content)


# #### BOT INITIALIZATION ####

user_data_manager = UserDataManager(tid_cache_dir)
bundles_cache = None

telegram_token = os.environ[env_vars['telegram_token']]
update_h = int(os.environ[env_vars['update_h']])
update_m = int(os.environ[env_vars['update_m']])

update_time = None
if 0 <= update_h < 24 and 0 <= update_m < 60:
    update_time = datetime.time(update_h, update_m)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logging.info("logger initialized")

updater = Updater(token=telegram_token)
dispatcher = updater.dispatcher

# register telegram callbacks

dispatcher.add_handler(CommandHandler("deals", comm_deals))
dispatcher.add_handler(CommandHandler("bundles", comm_bundles))
dispatcher.add_handler(CommandHandler("stats", comm_stats))
dispatcher.add_handler(CommandHandler("update", comm_update))
dispatcher.add_handler(CommandHandler("alldeals", comm_all_deals))
dispatcher.add_handler(CommandHandler("help", comm_help))

dispatcher.add_handler(
    ConversationHandler(entry_points=[CommandHandler("start", conv_start_start, pass_user_data=True)],
                        fallbacks=[CommandHandler("cancel", conv_cancel)], states={
            0: [MessageHandler(Filters.text, conv_start_username, pass_user_data=True)],
            1: [MessageHandler(Filters.text, conv_start_confirm, pass_user_data=True)]
        }))

dispatcher.add_handler(
    ConversationHandler(entry_points=[CommandHandler("settings", conv_settings_start, pass_user_data=True)],
                        fallbacks=[CommandHandler("cancel", conv_cancel)], states={
            0: [MessageHandler(Filters.text, conv_settings_set, pass_user_data=True)],
            1: [MessageHandler(Filters.text, conv_settings_apply, pass_user_data=True)],
            2: [MessageHandler(Filters.text, conv_settings_boolean, pass_user_data=True)]
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
    updater.job_queue.run_daily(job_bundles, update_time)
    updater.job_queue.run_daily(job_sporadic_notify, update_time)

if update_time is not None:
    logging.info("will send updates each day at {}".format(update_time))

# init bundles cache in background
updater.job_queue.run_once(job_bundles, datetime.datetime.now())

# program notifications send if needed
updater.job_queue.run_once(job_sporadic_notify, datetime.datetime.now()+datetime.timedelta(minutes=1))

# #### RUN BOT ####

logging.info("telegram bot initalized, starting")

updater.start_polling()

updater.idle()
