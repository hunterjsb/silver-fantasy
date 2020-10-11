from abc import ABC
import tornado.ioloop
import tornado.web
from updater import Updater


class MainHandler(tornado.web.RequestHandler, ABC):
    def initialize(self):
        print(f'hosting on port: idk')

    def set_default_headers(self):
        print("setting headers")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    async def get(self):
        print(f'GET {self.request.uri}, version 0.1')
        self.set_status(200, "data recv")
        u = Updater(self.get_query_argument("requestType"))  # initialize updater
        args = self.get_arguments("ign")

        resp = u.run(args)
        print(f'**************RESPONSE {resp}*************************************************************')
        self.write(resp)

    def post(self):
        print('POST!')
        self.set_status(200, "data recv")
        self.set_header("Content-Type", "text/plain")
        self.write("You wrote " + self.request.body)


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])


if __name__ == "__main__":
    app = make_app()
    app.listen(591, '157.245.247.40')
    tornado.ioloop.IOLoop.current().start()
