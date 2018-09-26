import recastai
import args
import time
import random
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer

from chat import Chat, Event


class Bot:
    def __init__(self, chat, options):
        self.chat = chat
        chat.subscriber = self.process
        self.started = time.time()

    def process(self, event, args):
        if event == Event.STATUS and args['user'] != self.chat.username and args['status'] == 'online':
            if time.time() - self.started > 3:
                self.chat.send(f"Hello {args['user']}")
        elif event == Event.NEW_MESSAGE and args['author'] != self.chat.username:
            self.chat.send(self.reply(args['text']))
        elif event == Event.PM and args['author'] != self.chat.username:
            self.chat.send(self.reply(args['text']), args['author'])

    def reply(self, msg):
        raise NotImplementedError


class RecastaiBot(Bot):
    def __init__(self, chat, options):
        super().__init__(chat, options)
        self.client = recastai.Client(options.token)

    def reply(self, msg):
        response = self.client.request.converse_text(msg)
        print(response.raw)
        return random.choice(response.replies)


class ChatterBot(Bot):
    def __init__(self, chat, options):
        super().__init__(chat, options)
        self.chatbot = ChatBot('Bot')
        trainer = ChatterBotCorpusTrainer(self.chatbot)
        trainer.train("chatterbot.corpus.english")

    def reply(self, msg):
        return self.chatbot.get_response(msg)


impls = {
    'recastai': RecastaiBot,
    'chatter': ChatterBot,
}

parser = args.create_parser()
parser.add_argument('bot', choices=impls.keys())
options = parser.parse_args()
options.token = '7eb8a157d82f1b52218413a4c68b880a'

bot = impls[options.bot](Chat(options), options)
bot.chat.connect()
