#!/usr/bin/env python2.7

import BaseHTTPServer

import collections
import os
import re
import socket
import sys
import signal
import time
import traceback
import urllib
import urlparse

from snmpy import log_error, VERSION

class HTTPError(Exception):
    code = 500
    def __init__(self, exception=None):
        self.line, self.body = Handler.responses[self.code]
        if exception is not None:
            self.body = ''.join(traceback.format_exception(*exception))

class HTTPForbiddenError(HTTPError):
    code = 403

class HTTPNotFoundError(HTTPError):
    code = 404


class Response():
    def __init__(self, **kwargs):
        self.__dict__.update({
            'code': 200,
            'line': 'OK',
            'head': collections.OrderedDict(),
            'body': '',
        })

        for key, val in kwargs.items():
            if key == 'head':
                self.head.update(kwargs['head'])
            else:
                setattr(self, key, val)

    def __setattr__(self, key, val):
        if key.startswith('_') or key == 'head' or key not in self.__dict__:
            raise AttributeError('setting attribute %s is not supported' % key)
        if key == 'code' and type(val) != int:
            raise AttributeError('setting attribute %s requires an integer' % key)

        self.__dict__[key] = val


class Server(BaseHTTPServer.HTTPServer):
    allow_reuse_address = True

    def __init__(self, port, addr='', **kwargs):
        BaseHTTPServer.HTTPServer.__init__(self, (addr, port), Handler)

        Handler.log_message     = lambda *args: True
        Handler.extra_settings  = collections.namedtuple('extra_settings', kwargs.keys())(*kwargs.values())
        Handler.server_version += ' %s/%s' % (__name__, VERSION)

        self.serve_forever(poll_interval=None)

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_TCP, socket.TCP_DEFER_ACCEPT, True)
        self.socket.setsockopt(socket.SOL_TCP, socket.TCP_QUICKACK,     True)
        BaseHTTPServer.HTTPServer.server_bind(self)

    def process_request(self, *args):
        def handle_timeout(*args):
            raise RuntimeError('request timed out')

        try:
            signal.signal(signal.SIGALRM, handle_timeout)
            signal.alarm(10)

            BaseHTTPServer.HTTPServer.process_request(self, *args)
        except Exception as e:
            log_error(e)
        finally:
            signal.alarm(0)


class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    request_handlers = {
        'GET': collections.OrderedDict()
    }

    default_headers = {
        'Connection': 'close',
        'Content-type': 'text/plain',
    }

    def route_request(self, method):
        self.start_time  = time.time() * 1000

        self.url   = urlparse.urlparse(self.path)
        self.path  = urllib.unquote(self.url.path)
        self.query = urlparse.parse_qs(self.url.query)

        response = Response(head=self.default_headers)

        try:
            for patt, func in self.request_handlers[method].items():
                find = patt.match(self.path)
                if find:
                    response = Response(head=self.default_headers)
                    func(self, response, *(find.groups()))
                    break
            else:
                raise HTTPNotFoundError

        except Exception as e:
            if not isinstance(e, HTTPError):
                e = HTTPError(sys.exc_info())
            response.code = e.code
            response.line = e.line
            response.body = e.body

        self.send_response(response.code, response.line)
        for key, val in response.head.items():
            if key.lower() != 'content-length':
                self.send_header(key, val)
        self.send_header('Content-length', len(response.body))
        self.send_header('X-Handler-Time', '%.02fms' % (time.time() * 1000 - self.start_time))
        self.send_header('X-Handler-Pid', os.getpid())
        self.end_headers()
        self.wfile.write(response.body)

    def do_GET(self):
        self.route_request('GET')

def GET(path=None):
    def wrapper(func):
        patt = r'/%s(?:/|$)' % (path.strip('/') if path is not None else func.func_name.replace('_', '-'))
        Handler.request_handlers['GET'][re.compile(patt)] = func
    return wrapper


@GET()
def version(req, res):
    res.body = req.server_version + '\r\n'
