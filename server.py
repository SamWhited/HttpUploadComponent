#!/usr/bin/env python

import argparse
import errno
import hashlib
import logging
import mimetypes
import os
import urlparse
import random
import shutil
import ssl
import string
import sys
import time
import yaml

from sleekxmpp.componentxmpp import ComponentXMPP
from threading import Event
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
global quotas

def normalize_path(path, sub_url_length):
    """
    Normalizes the URL to prevent users from grabbing arbitrary files via `../'
    and the like.
    """
    return os.path.normcase(os.path.normpath(path))[sub_url_length:]

def expire(quotaonly=False, kill_event=None):
    """
    Expire all files over 'user_quota_soft' and older than 'expire_maxage'

        - quotaonly - If true don't delete anything just calculate the
          used space per user and return. Otherwise make an exiry run
          every config['expire_interval'] seconds.
        - kill_event - threading.Event to listen to. When set, quit to
          prevent hanging on KeyboardInterrupt. Only applicable when
          quotaonly = False
    """
    global config
    global quotas

    while True:
        if not quotaonly:
            # Wait expire_interval secs or return on kill_event
            if kill_event.wait(config['expire_interval']):
                return

        now = time.time()
        # Scan each senders upload directories seperatly
        for sender in os.listdir(config['storage_path']):
            senderdir = os.path.join(config['storage_path'], sender)
            quota = 0
            filelist = []
            # Traverse sender directory, delete anything older expire_maxage and collect file stats.
            for dirname, dirs, files in os.walk(senderdir, topdown=False):
                removed = []
                for name in files:
                    fullname = os.path.join(dirname, name)
                    stats = os.stat(fullname)
                    if not quotaonly:
                        if now - stats.st_mtime > config['expire_maxage']:
                            logging.debug('Expiring %s. Age: %s', fullname, now - stats.st_mtime)
                            try:
                                os.unlink(fullname)
                                removed += [name]
                            except OSError as e:
                                logging.warning("Exception '%s' deleting file '%s'.", e, fullname)
                                quota += stats.st_size
                                filelist += [(stats.st_mtime, fullname, stats.st_size)]
                        else:
                            quota += stats.st_size
                            filelist += [(stats.st_mtime, fullname, stats.st_size)]
                if dirs == [] and removed == files:    # Directory is empty, so we can remove it
                    logging.debug('Removing directory %s.', dirname)
                    try:
                            os.rmdir(dirname)
                    except OSError as e:
                            logging.warning("Exception '%s' deleting directory '%s'.", e, dirname)

            if not quotaonly and config['user_quota_soft']:
                # Delete oldest files of sender until occupied space is <= user_quota_soft
                filelist.sort()
                while quota > config['user_quota_soft']:
                    entry = filelist[0]
                    try:
                        logging.debug('user_quota_soft exceeded. Removing %s. Age: %s', entry[1], now - entry[0])
                        os.unlink(entry[1])
                        quota -= entry[2]
                    except OSError as e:
                        logging.warning("Exception '%s' deleting file '%s'.", e, entry[1])
                    filelist.pop(0)
            quotas[sender] = quota

        logging.debug('Expire run finished in %fs', time.time() - now)

        if quotaonly:
            return


class MissingComponent(ComponentXMPP):
    def __init__(self, jid, secret, port):
        ComponentXMPP.__init__(self, jid, secret, "localhost", port)
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
        elif 'whitelist' not in config or iq['from'].domain in config['whitelist'] or iq['from'].bare in config['whitelist']:
            sender = iq['from'].bare
            sender_hash = hashlib.sha1(sender.encode()).hexdigest()
            if config['user_quota_hard'] and quotas.setdefault(sender_hash, 0) + int(request['size']) > config['user_quota_hard']:
                msg = 'quota would be exceeded. max file size is %d' % (config['user_quota_hard'] - quotas[sender_hash])
                logging.debug(msg)
                self._sendError(iq, 'modify', 'not-acceptable', msg)
                return
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
            reply['slot']['get'] = urlparse.urljoin(config['get_url'], path)
            reply['slot']['put'] = urlparse.urljoin(config['put_url'], path)
            reply.send()
        else:
            self._sendError(iq,'cancel','not-allowed','not allowed to request upload slots')

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
        path = normalize_path(self.path, config['put_sub_url_len'])
        length = int(self.headers['Content-Length'])
        maxfilesize = int(config['max_file_size'])
        if config['user_quota_hard']:
            sender_hash = path.split('/')[0]
            maxfilesize = min(maxfilesize, config['user_quota_hard'] - quotas.setdefault(sender_hash, 0))
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
                with open(filename,'wb') as f:
                    data = self.rfile.read(min(4096,remaining))
                    while data and remaining >= 0:
                        databytes = len(data)
                        remaining -= databytes
                        if config['user_quota_hard']:
                            quotas[sender_hash] += databytes
                        f.write(data)
                        data = self.rfile.read(min(4096,remaining))
                self.send_response(200,'ok')
                self.end_headers()
            else:
                files_lock.release()
                self.send_response(403,'invalid slot')
                self.end_headers()

    def do_GET(self, body=True):
        global config
        path = normalize_path(self.path, config['get_sub_url_len'])
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
                    mime, _ = mimetypes.guess_type(filename)
                    if mime is None:
                        mime = 'application/octet-stream'
                    self.send_header("Content-Type", mime)
                    if mime[:6] != 'image/':
                        self.send_header("Content-Disposition", 'attachment; filename="{}"'.format(os.path.basename(filename)))
                    fs = os.fstat(f.fileno())
                    self.send_header("Content-Length", str(fs.st_size))
                    self.end_headers()
                    if body:
                        shutil.copyfileobj(f, self.wfile)
            except FileNotFoundError:
                self.send_response(404,'file not found')
                self.end_headers()

    def do_HEAD(self):
        self.do_GET(body=False)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default='config.yml', help='Specify alternate config file.')
    parser.add_argument("-l", "--logfile", default=None, help='File where the server log will be stored. If not specified log to stdout.')
    args = parser.parse_args()

    with open(args.config,'r') as ymlfile:
        config = yaml.load(ymlfile)

    files = set()
    files_lock = Lock()
    kill_event = Event()
    logging.basicConfig(level=LOGLEVEL,
                            format='%(asctime)-24s %(levelname)-8s %(message)s',
                            filename=args.logfile)

    if not config['get_url'].endswith('/'):
        config['get_url'] = config['get_url'] + '/'
    if not config['put_url'].endswith('/'):
        config['put_url'] = config['put_url'] + '/'

    try:
        config['get_sub_url_len'] = len(urlparse.urlparse(config['get_url']).path)
        config['put_sub_url_len'] = len(urlparse.urlparse(config['put_url']).path)
    except ValueError:
        logging.warning("Invalid get_sub_url ('%s') or put_sub_url ('%s'). sub_url's disabled.", config['get_sub_url'], config['put_sub_url'])
        config['get_sub_url_int'] = 1
        config['put_sub_url_int'] = 1

    # Sanitize config['user_quota_*'] and calculate initial quotas
    quotas = {}
    try:
        config['user_quota_hard'] = int(config.get('user_quota_hard', 0))
        config['user_quota_soft'] = int(config.get('user_quota_soft', 0))
        if config['user_quota_soft'] or config['user_quota_hard']:
            expire(quotaonly=True)
    except ValueError:
        logging.warning("Invalid user_quota_hard ('%s') or user_quota_soft ('%s'). Quotas disabled.", config['user_quota_soft'], config['user_quota_soft'])
        config['user_quota_soft'] = 0
        config['user_quota_hard'] = 0

    # Sanitize config['expire_*'] and start expiry thread
    try:
        config['expire_interval'] = float(config.get('expire_interval', 0))
        config['expire_maxage'] = float(config.get('expire_maxage', 0))
        if config['expire_interval'] > 0 and (config['user_quota_soft'] or config['expire_maxage']):
            t = Thread(target=expire, kwargs={'kill_event': kill_event})
            t.start()
        else:
            logging.info('Expiring disabled.')
    except ValueError:
        logging.warning("Invalid expire_interval ('%s') or expire_maxage ('%s') set in config file. Expiring disabled.",
                        config['expire_interval'], config['expire_maxage'])

    try:
        server = ThreadedHTTPServer((config['http_address'], config['http_port']), HttpHandler)
    except Exception as e:
        import traceback
        logging.debug(traceback.format_exc())
        kill_event.set()
        sys.exit(1)

    if 'http_keyfile' in config and 'http_certfile' in config:
        server.socket = ssl.wrap_socket(server.socket, keyfile=config['http_keyfile'], certfile=config['http_certfile'])
    jid = config['component_jid']
    secret = config['component_secret']
    port = int(config.get('component_port',5347))
    xmpp = MissingComponent(jid,secret,port)
    if xmpp.connect():
        xmpp.process()
        print("connected")
        try:
            server.serve_forever()
        except (KeyboardInterrupt, Exception) as e:
            if e == KeyboardInterrupt:
                logging.debug('Ctrl+C pressed')
            else:
                import traceback
                logging.debug(traceback.format_exc())
            kill_event.set()
    else:
        print("unable to connect")
        kill_event.set()
