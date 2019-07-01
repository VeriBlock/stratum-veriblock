from stratum.pubsub import Pubsub, Subscription
from mining.interfaces import Interfaces

import stratum.logger
log = stratum.logger.get_logger('subscription')

class MiningSubscription(Subscription):
    '''This subscription object implements
    logic for broadcasting new jobs to the clients.'''

    event = 'mining.notify'

    @classmethod
    def on_template(cls, is_new_block):
        '''This is called when TemplateRegistry registers
           new block which we have to broadcast clients.'''

        start = Interfaces.timestamper.time()

        clean_jobs = is_new_block
        (job_id, height, version, prevhash, prevkeystone, secondkeystone, intermediate_merkles, time, difficulty, clean_jobs) = \
                        Interfaces.template_registry.get_last_broadcast_args()

        # Push new job to subscribed clients
        cls.emit(job_id, height, version, prevhash, prevkeystone, secondkeystone, intermediate_merkles, time, difficulty, clean_jobs)

        cnt = Pubsub.get_subscription_count(cls.event)
        log.info("BROADCASTED to %d connections in %.03f sec" % (cnt, (Interfaces.timestamper.time() - start)))

    def _finish_after_subscribe(self, result):
        '''Send new job to newly subscribed client'''
        try:
            session = self.connection_ref().get_session()
            difficulty = session['difficulty']
            self.connection_ref().rpc('mining.set_difficulty', [str(difficulty), ], is_notification=True)

            (job_id, height, version, prevhash, prevkeystone, secondkeystone, intermediate_merkles, time, difficulty, clean_jobs) = \
                        Interfaces.template_registry.get_last_broadcast_args()

        except Exception:
            log.error("Template not ready yet")
            return result

        # Force client to remove previous jobs if any (eg. from previous connection)
        clean_jobs = True
        self.emit_single(job_id, height, version, prevhash, prevkeystone, secondkeystone, intermediate_merkles, time, difficulty, True)

        return result

    def after_subscribe(self, *args):
        '''This will send new job to the client *after* he receive subscription details.
        on_finish callback solve the issue that job is broadcasted *during*
        the subscription request and client receive messages in wrong order.'''
        self.connection_ref().on_finish.addCallback(self._finish_after_subscribe)

    def __hash__(self):
        return hash(repr(self.connection_ref))
