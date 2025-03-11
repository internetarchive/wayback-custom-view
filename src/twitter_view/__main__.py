import os
from argparse import ArgumentParser
from werkzeug.serving import run_simple
from werkzeug.middleware.shared_data import SharedDataMiddleware

from .twitter_view_app import CustomViewTwitterApp

def bind_addr(v):
    host, _, port = v.partition(':')
    return host or None, port and int(port) or None

parser = ArgumentParser()
parser.add_argument('-b', '--bind', type=bind_addr, default=bind_addr(''))

args = parser.parse_args()

base_app = CustomViewTwitterApp()
application = SharedDataMiddleware(base_app, {
    '/_static': os.path.join(os.path.dirname(__file__), 'static')
})
host, port = args.bind
run_simple(host or 'localhost', port or 5000, application,
    use_reloader=True, use_debugger=True)
