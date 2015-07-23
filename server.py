#!/usr/bin/env python

import argparse
import errno
import hashlib
import logging
import mimetypes
import os
import random
import shutil
import signal
import sleekxmpp
import ssl
import string
import sys
import yaml

from sleekxmpp.componentxmpp import ComponentXMPP
from threading import Lock
from threading import Thread

try:
    # Python 3
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from socketserver import ThreadingMixIn
except ImportError:
    # Python 2
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SocketServer import ThreadingMixIn

try:
    FileNotFoundError
except NameError:
    # Python 2
    class FileNotFoundError(IOError):
        def __init__(self, message=None, *args):
            super(FileNotFoundError, self).__init__(args)
            self.message = message
            self.errno = errno.ENOENT

        def __str__(self):
            return self.message or os.strerror(self.errno)


LOGLEVEL=logging.DEBUG

global files
global files_lock
global config

def normalize_path(path):
    """
    Normalizes the URL to prevent users from grabbing arbitrary files via `../'
    and the like.
    """
    return os.path.normcase(os.path.normpath(path))

class MissingComponent(ComponentXMPP):
    def __init__(self, jid, secret):
        ComponentXMPP.__init__(self, jid, secret, "localhost", 5347)
        self.register_plugin('xep_0030')
        self.register_plugin('upload',module='plugins.upload')
        self.add_event_handler('request_upload_slot',self.request_upload_slot)

    def request_upload_slot(self, iq):
        global config
        global files
        global files_lock
        request = iq['request']
        maxfilesize = int(config['max_file_size'])
        if not request['filename'] or not request['size']:
            self._sendError(iq,'modify','bad-request','please specify filename and size')
        elif maxfilesize < int(request['size']):
            self._sendError(iq,'modify','not-acceptable','file too large. max file size is '+str(maxfilesize))
        elif 'whitelist' not in config or iq['from'].domain in config['whitelist']:
            sender = iq['from'].bare
            sender_hash = hashlib.sha1(sender.encode()).hexdigest()
            filename = request['filename']
            folder = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(len(sender_hash)))
            sane_filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c=="."]).rstrip()
            path = os.path.join(sender_hash, folder)
            if sane_filename:
                path = os.path.join(path, sane_filename)
            with files_lock:
                files.add(path)
            print(path)
            reply = iq.reply()
            reply['slot']['get'] = os.path.join(config['get_url'], path)
            reply['slot']['put'] = os.path.join(config['put_url'], path)
            reply.send()
        else:
           self. _sendError(iq,'cancel','not-allowed','not allowed to request upload slots')

    def _sendError(self, iq, error_type, condition, text):
        reply = iq.reply()
        iq.error()
        iq['error']['type'] = error_type
        iq['error']['condition'] = condition
        iq['error']['text'] = text
        iq.send()

class HttpHandler(BaseHTTPRequestHandler):
    def do_PUT(self):
        print('do put')
        global files
        global files_lock
        global config
        path = normalize_path(self.path[1:])
        length = int(self.headers['Content-Length'])
        maxfilesize = int(config['max_file_size'])
        if maxfilesize < length:
            self.send_response(400,'file too large')
            self.end_headers()
        else:
            print('path: '+path)
            files_lock.acquire()
            if path in files:
                files.remove(path)
                files_lock.release()
                filename = os.path.join(config['storage_path'], path)
                os.makedirs(os.path.dirname(filename))
                remaining = length
                f = open(filename,'wb')
                data = self.rfile.read(4096)
                while data and remaining >= 0:
                    remaining -= len(data)
                    f.write(data)
                    data = self.rfile.read(min(4096,remaining))
                f.close()
                self.send_response(200,'ok')
                self.end_headers()
            else:
                files_lock.release()
                self.send_response(403,'invalid slot')
                self.end_headers()

    def do_GET(self):
        global config
        path = normalize_path(self.path[1:])
        slashcount = path.count('/')
        if path[0] in ('/', '\\') or slashcount < 1 or slashcount > 2:
            self.send_response(404,'file not found')
            self.end_headers()
        else:
            filename = os.path.join(config['storage_path'], path)
            print('requesting file: '+filename)
            try:
                with open(filename,'rb') as f:
                    self.send_response(200)
                    self.send_header("Content-Type", 'application/octet-stream')
                    self.send_header("Content-Disposition", 'attachment; filename="{}"'.format(os.path.basename(filename)))
                    fs = os.fstat(f.fileno())
                    self.send_header("Content-Length", str(fs.st_size))
                    self.end_headers()
                    shutil.copyfileobj(f, self.wfile)
            except FileNotFoundError:
                self.send_response(404,'file not found')
                self.end_headers()

    def do_HEAD(self):
        global config
        path = normalize_path(self.path[1:])
        slashcount = path.count('/')
        if path[0] in ('/', '\\') or slashcount < 1 or slashcount > 2:
            self.send_response(404,'file not found')
            self.end_headers()
        else:
            try:
                filename = os.path.join(config['storage_path'], path)
                self.send_response(200,'OK')
                self.send_header("Content-Type", 'application/octet-stream')
                self.send_header("Content-Disposition", 'attachment; filename="{}"'.format(os.path.basename(filename)))
                self.send_header("Content-Length",str(os.path.getsize(filename)))
                self.end_headers()
            except FileNotFoundError:
                self.send_response(404,'file not found')
                self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == "__main__":
    global files
    global files_lock
    global config

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=unicode, default='config.yml', help='Specify alternate config file.')
    parser.add_argument("-l", "--logfile", type=unicode, default=None, help='File where the server log will be stored. If not specified log to stdout.')
    args = parser.parse_args()

    with open(args.config,'r') as ymlfile:
        config = yaml.load(ymlfile)

    files = set()
    files_lock = Lock()
    logging.basicConfig(level=LOGLEVEL,
                            format='%(asctime)-24s %(levelname)-8s %(message)s',
                            filename=args.logfile)
    server = ThreadedHTTPServer((config['http_address'], config['http_port']), HttpHandler)
    if 'keyfile' in config and 'certfile' in config:
        server.socket = ssl.wrap_socket(server.socket, keyfile=config['keyfile'], certfile=config['certfile'])
    xmpp = MissingComponent(config['jid'],config['secret'])
    if xmpp.connect():
        xmpp.process()
        print("connected")
        server.serve_forever()
    else:
        print("unable to connect")
