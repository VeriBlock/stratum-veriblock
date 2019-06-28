import weakref

import simplejson as json
from twisted.internet import reactor, defer
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import LineOnlyReceiver

from .block_template import BlockTemplate

import stratum.logger
log = stratum.logger.get_logger('veriblock_ucp')

class VeriBlockUCP(LineOnlyReceiver):

    def __init__(self, timestamper, username):
        self.timestamper = timestamper
        self.username = username
        self.delimiter = '\n'.encode('utf8')
        self.request_id_counter = 0
        self.requests = weakref.WeakValueDictionary()
        self.on_connected = defer.Deferred()
        self.on_mining_job_callback = None

    def connectionMade(self):
        log.info("CONNECTION ESTABLISHED")
        self.authenticate()
        self.on_connected.callback(True)

    def lineReceived(self, line):
        command = json.loads(line)
        log.info(line)
        if command['command'] == "MINING_AUTH_SUCCESS":
            self.on_auth_success()
        elif command['command'] == "MINING_SUBMIT_SUCCESS":
            self.on_submit_success(command)
        elif command['command'] == "MINING_SUBMIT_FAILURE":
            self.on_submit_failure(command)
        elif command['command'] == "MINING_JOB":
            self.on_mining_job(command)

    def _next_request_id(self):
        self.request_id_counter += 1
        return self.request_id_counter

    def _send(self, command):
        command_string = json.dumps(command, ensure_ascii=False).encode('utf8')
        self.sendLine(command_string)

    def set_mining_job_callback(self, callback):
        self.on_mining_job_callback = callback

    def authenticate(self):
        command = {
            'command':'MINING_AUTH',
            'request_id': {
                'type':'REQUEST_ID',
                'data': self._next_request_id()
            },
            'username': {
                'type':'USERNAME',
                'data': self.username
            },
            'password': {
                'type':'PASSWORD',
                'data':''
            }
        }
        self._send(command)

    def subscribe(self):
        command = {
            'command':'MINING_SUBSCRIBE',
            'request_id': {
                'type':'REQUEST_ID',
                'data': self._next_request_id()
            },
            'update_frequency_ms': {
                'type':'FREQUENCY_MS',
                'data':5000
            }
        }
        self._send(command)

    def submit_share(self, job_id, extranonce, timestamp, nonce):
        d = defer.Deferred()
        request_id = self._next_request_id()
        command = {
            'command':'MINING_SUBMIT',
            'request_id': {
                'type':'REQUEST_ID',
                'data': request_id
            },
            'job_id': {
                'type':'JOB_ID',
                'data': job_id
            },
            'nTime': {
                'type':'TIMESTAMP',
                'data': timestamp
            },
            'nonce': {
                'type':'NONCE',
                'data': nonce
            },
            'extra_nonce': {
                'type':'EXTRA_NONCE',
                'data': extranonce
            }
        }
        self.requests[request_id] = d
        self._send(command)

        return d

    def on_auth_success(self):
        self.subscribe()

    def on_submit_success(self, command):
        request_id = command['request_id']['data']
        try:
            d = self.requests[request_id]
        except:
            return
        
        d.callback(True)

    def on_submit_failure(self, command):
        request_id = command['request_id']['data']
        try:
            d = self.requests[request_id]
        except:
            return
        
        d.callback(False)

    def on_mining_job(self, job):
        template = BlockTemplate(self.timestamper, str(job['request_id']['data']))
        template.fill_from_job(job)
        if self.on_mining_job_callback is not None:
            self.on_mining_job_callback(template)

class UCPClientFactory(ReconnectingClientFactory):
    def __init__(self, protocol):
        self.protocol = protocol

    def buildProtocol(self, addr):
        self.resetDelay()
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        print("Connection failed:", reason)
        reactor.stop()