from telebot import TeleBot, apihelper
from pymongo import MongoClient
from configparser import ConfigParser
import threading
import time


class Conf:
    """yet another config parser"""
    class ConfSection:
        def __init__(self):
            pass

    def __init__(self, config_file):
        self._config = ConfigParser()
        self._config.read(config_file)
        self._parse()

    def _parse(self):
        for section in self._config.sections():
            setattr(self, section, self.ConfSection)
            for line in self._config[section]:
                attribute = getattr(self, section)
                setattr(attribute, line, self._config[section][line])


class Statistic:
    """instance of statistic for current chat"""
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.message = str()
        self.user_list = list()
        self.stats = None
        self.exhume_stats()

    @staticmethod
    def fix_username(user): # die fucktards without username!
        try:
            user["username"] = user["username"]
        except:
            try:
                user["username"] = user["first_name"]
            except:
                try:
                    user["username"] = user["second_name"]
                except:
                    user["username"] = str(user["id"])
        return user["username"]

    def exhume_stats(self):
        result = chats.find({"chat_id": self.chat_id}, {"users": 1, "_id": 0})
        try:
            self.user_list = dict(result[0])["users"]
        except:
            pass

        self.stats = (sorted(self.user_list, key=lambda k: k['message_count']))
        self.prepare_message()

    def prepare_message(self):
        self.message = str()
        for item in self.stats:
            self.message = self.message + self.fix_username(item) + " -- " + str(item["message_count"]) + "\n"


# Initial configuration

config = Conf("config.ini")
connection = MongoClient(config.db.address)
db = connection[config.db.name]
chats = db[config.db.collection]
app = TeleBot(config.bot.token)
if hasattr(config.bot, "proxy"):
    print ("starting with proxy")
    apihelper.proxy = {'https': 'socks5h://'+config.bot.proxy}


def bot_polling(app):
    crash_count = 0
    while True:
        try:
            print("bot started")
            app.polling(none_stop=True)
        except Exception as e:
            crash_count += 1
            print(e)
            print(crash_count, "crush detected, will take a brief")
            time.sleep(15)
            print("restarting...")


def update_user(message):
    # on new message try to increment message count of existing user
    result = chats.find_one_and_update(
        {
            "chat_id": message.chat.id,
            "users.id": message.from_user.id
        },
        {
            "$inc": {"users.$.message_count": 1}
        }
    )

    if result is None:  # if no user within specific chat id found - add this user to chat
        user_info = (message.json["from"])
        user_info.update({"message_count": 1})
        chats.find_one_and_update({"chat_id": message.chat.id}, {"$push": {"users": user_info}})


@app.message_handler(commands=['about'])
def about(message):
    app.send_message(message.chat.id, "Hello, this is typical chat cleaner wich used to keep friendly and "
                                      "private environment. This bot do not store any message history, "
                                      "media content or personal user info. This bot stores metadata like"
                                      " userID, chatID, and count messages in different ways.")


@app.message_handler(commands=['help'])
def show_help(message):
    app.send_message(message.chat.id, "List of possible commands:\n"
                                      "/start - Turns on message processing and statistic collection\n"
                                      "/about - Disclaimer\n"
                                      "/stats - prints message statistic")


@app.message_handler(commands=['start'])
def start(message):
    result = chats.find_one({"chat_id": message.chat.id})
    if result is not None:
        app.send_message(message.chat.id, 'Bot already operating in this chat')
    else:
        chats.insert_one({
            "chat_name": message.chat.title,
            "chat_id": message.chat.id,
            "users": []
        })


@app.message_handler(commands=['stats'])
def stats(message):
    statistic_instance = Statistic(message.chat.id)
    app.send_message(message.chat.id, statistic_instance.message)


@app.message_handler(func=lambda message: True, content_types=['text','new_chat_participant'])
def general_handler(message):
    update_user(message)


if __name__ == '__main__':
    polling_thread = threading.Thread(target=bot_polling, args=(app,))
    polling_thread.start()
