import time

from .service import MiningService
from .subscription import MiningSubscription
from twisted.internet import defer, reactor

@defer.inlineCallbacks
def setup(on_startup):
    '''Setup mining service internal environment.
    You should not need to change this. If you
    want to use another Worker manager or Share manager,
    you should set proper reference to Interfaces class
    *before* you call setup() in the launcher script.'''

    import stratum.logger
    log = stratum.logger.get_logger('mining')

    from stratum import settings
    from .interfaces import Interfaces

    # Let's wait until share manager and worker manager boot up
    (yield Interfaces.share_manager.on_load)
    (yield Interfaces.worker_manager.on_load)

    from lib.template_registry import TemplateRegistry
    from lib.veriblock_ucp import VeriBlockUCP, UCPClientFactory

    veriblock_ucp = VeriBlockUCP(Interfaces.timestamper, settings.CENTRAL_WALLET)
    factory = UCPClientFactory(veriblock_ucp)
    log.info('Waiting for VeriBlock UCP...')

    registry = TemplateRegistry(veriblock_ucp,
                                settings.INSTANCE_ID,
                                MiningSubscription.on_template,
                                Interfaces.share_manager.on_network_block)

    # Template registry is the main interface between Stratum service
    # and pool core logic
    Interfaces.set_template_registry(registry)

    veriblock_ucp.set_mining_job_callback(registry.add_template)

    reactor.connectTCP(settings.NODECORE_HOST, settings.NODECORE_PORT, factory)

    log.info("MINING SERVICE IS READY")
    on_startup.callback(True)
