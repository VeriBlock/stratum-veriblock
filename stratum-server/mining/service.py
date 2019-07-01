import binascii
from twisted.internet import defer

from stratum.services import GenericService, admin
from stratum.pubsub import Pubsub
import stratum.settings as settings
from .interfaces import Interfaces
from .subscription import MiningSubscription
from lib.exceptions import SubmitException

import stratum.logger
log = stratum.logger.get_logger('mining')

class MiningService(GenericService):
    '''This service provides public API for Stratum mining proxy
    or any Stratum-compatible miner software.

    Warning - any callable argument of this class will be propagated
    over Stratum protocol for public audience!'''

    service_type = 'mining'
    service_vendor = 'stratum'
    is_default = True

    def authorize(self, worker_name, worker_password):
        '''Let authorize worker on this connection.'''

        session = self.connection_ref().get_session()
        session.setdefault('authorized', {})

        if Interfaces.worker_manager.authorize(worker_name, worker_password):
            session['authorized'][worker_name] = worker_password
            return True

        else:
            if worker_name in session['authorized']:
                del session['authorized'][worker_name]
            return False

    def subscribe(self, *args):
        '''Subscribe for receiving mining jobs. This will
        return subscription details, extranonce_hex and extranonce_size'''

        extranonce = Interfaces.template_registry.get_new_extranonce()
        extranonce_size = Interfaces.template_registry.extranonce_size
        extranonce_hex = binascii.hexlify(extranonce).decode('utf_8')

        session = self.connection_ref().get_session()
        session['extranonce'] = extranonce
        session['difficulty'] = settings.POOL_TARGET

        return Pubsub.subscribe(self.connection_ref(), MiningSubscription()) + (extranonce_hex, extranonce_size)

    def submit(self, worker_name, job_id, extranonce, ntime, nonce):
        '''Try to solve block candidate using given parameters.'''

        session = self.connection_ref().get_session()
        session.setdefault('authorized', {})

        # Check if worker is authorized to submit shares
        if not Interfaces.worker_manager.authorize(worker_name,
                        session['authorized'].get(worker_name)):
            raise SubmitException("Worker is not authorized")

        # Check if extranonce is in connection session
        extranonce_bin = session.get('extranonce', None)
        if not extranonce_bin:
            raise SubmitException("Connection is not subscribed for mining")

        difficulty = session['difficulty']
        submit_time = Interfaces.timestamper.time()

        Interfaces.share_limiter.submit(self.connection_ref, job_id, difficulty, submit_time, worker_name)

        # This checks if submitted share meet all requirements
        # and it is valid proof of work.
        try:
            (block_header, block_hash, on_submit) = Interfaces.template_registry.submit_share(job_id,
                                                worker_name, extranonce, ntime, nonce, difficulty)
        except SubmitException:
            # block_header and block_hash are None when submitted data are corrupted
            Interfaces.share_manager.on_submit_share(worker_name, None, None, difficulty,
                                                 submit_time, False)
            raise


        Interfaces.share_manager.on_submit_share(worker_name, block_header, block_hash, difficulty,
                                                 submit_time, True)

        if on_submit != None:
            # Pool sends MINING_SUBMIT to NodeCore. Let's hook
            # to result and report it to share manager
            on_submit.addCallback(Interfaces.share_manager.on_submit_block,
                        worker_name, block_header, block_hash, submit_time)

        return True

    # Service documentation for remote discovery

    authorize.help_text = "Authorize worker for submitting shares on this connection."
    authorize.params = [('worker_name', 'string', 'Name of the worker, usually in the form of user_login.worker_id.'),
                        ('worker_password', 'string', 'Worker password'),]

    subscribe.help_text = "Subscribes current connection for receiving new mining jobs."
    subscribe.params = []

    submit.help_text = "Submit solved share back to the server. Excessive sending of invalid shares "\
                       "or shares above indicated target (see Stratum mining docs for set_target()) may lead "\
                       "to temporary or permanent ban of user,worker or IP address."
    submit.params = [('worker_name', 'string', 'Name of the worker, usually in the form of user_login.worker_id.'),
                     ('job_id', 'string', 'ID of job (received by mining.notify) which the current solution is based on.'),
                     ('extranonce', 'string', '64bit integer, big-endian, hex-encoded extranonce'),
                     ('timestamp', 'string', 'UNIX timestamp (32bit integer, big-endian, hex-encoded), must be >= ntime provided by mining.notify and <= current time'),
                     ('nonce', 'string', '32bit integer, big-endian, hex-encoded')]

