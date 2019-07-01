# ******************** GENERAL SETTINGS ***************

# Enable some verbose debug (logging requests and responses).
DEBUG = False

# Destination for application logs, files rotated once per day.
LOGDIR = 'log/'

# Main application log file.
LOGFILE = None#'stratum.log'

# Possible values: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOGLEVEL = 'INFO'

# How many threads use for synchronous methods (services).
# 30 is enough for small installation, for real usage
# it should be slightly more, say 100-300.
THREAD_POOL_SIZE = 30

ENABLE_EXAMPLE_SERVICE = False

# ******************** TRANSPORTS *********************

# Hostname or external IP to expose
HOSTNAME = '127.0.0.1'

# Port used for Socket transport. Use 'None' for disabling the transport.
LISTEN_SOCKET_TRANSPORT = 3333

# Port used for HTTP Poll transport. Use 'None' for disabling the transport
LISTEN_HTTP_TRANSPORT = None

# Port used for HTTPS Poll transport
LISTEN_HTTPS_TRANSPORT = None

# Port used for WebSocket transport, 'None' for disabling WS
LISTEN_WS_TRANSPORT = None

# Port used for secure WebSocket, 'None' for disabling WSS
LISTEN_WSS_TRANSPORT = None

# Pool related settings
INSTANCE_ID = 31
CENTRAL_WALLET = 'VFMJSUgJCy9QRa1RjXNmJ5kLy5D35C'

NODECORE_HOST = "127.0.0.1"
NODECORE_PORT = 8501

# ******************** Pool Difficulty Settings *********************
VDIFF_X2_TYPE = True            # Powers of 2 e.g. 2,4,8,16,32,64,128,256,512,1024
VDIFF_FLOAT = False             # Use float difficulty

# Pool Target (Base Difficulty)
POOL_TARGET = 0x100000                # Pool-wide difficulty target int >= 1

# Variable Difficulty Enable
VARIABLE_DIFF = True            # Master variable difficulty enable

# Variable diff tuning variables
#VARDIFF will start at the POOL_TARGET. It can go as low as the VDIFF_MIN and as high as min(VDIFF_MAX or coindaemons difficulty)
VDIFF_MIN_TARGET = 0x10000                # Minimum target difficulty 
VDIFF_MAX_TARGET = 0x1000000000000         # Maximum target difficulty 
VDIFF_MIN_CHANGE = 0xFFF            # Minimum change of worker's difficulty if VDIFF_X2_TYPE=False and the final difficulty will be within the boundaries (VDIFF_MIN_TARGET, VDIFF_MAX_TARGET)
VDIFF_TARGET_TIME = 10          # Target time per share (i.e. try to get 1 share per this many seconds)
VDIFF_RETARGET_TIME = 120       # How often the miners difficulty changes if appropriate
VDIFF_VARIANCE_PERCENT = 30     # Allow average time to very this % from target without retarget