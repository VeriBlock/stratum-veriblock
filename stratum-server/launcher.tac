# Run me with "twistd -ny launcher_demo.tac -l -"

# Add conf directory to python path.
# Configuration file is standard python module.
import os
import sys
TWISTED_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(TWISTED_DIR)
sys.path.append(os.path.join(TWISTED_DIR, 'conf'))

from twisted.internet import defer

# Run listening when mining service is ready
on_startup = defer.Deferred()

# Bootstrap Stratum framework
import stratum
from stratum import settings
application = stratum.setup(on_startup)

# Load mining service into stratum framework
import mining

from mining.interfaces import Interfaces
from mining.interfaces import WorkerManagerInterface, TimestamperInterface, \
                            ShareManagerInterface, ShareLimiterInterface

Interfaces.set_share_manager(ShareManagerInterface())
Interfaces.set_share_limiter(ShareLimiterInterface())
Interfaces.set_worker_manager(WorkerManagerInterface())
Interfaces.set_timestamper(TimestamperInterface())

mining.setup(on_startup)
