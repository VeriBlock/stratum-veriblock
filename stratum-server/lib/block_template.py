import binascii
import struct

from Crypto.Hash import SHA256

import vblake
import lib.util as util
from lib.merkletree import MerkleTree

# Remove dependency to settings, coinbase extras should be
# provided from coinbaser
# from stratum import settings

class BlockTemplate:
    '''Template is used for generating new jobs for clients.
    Let's iterate extranonce, ntime and nonce
    to find out valid block!'''

    def __init__(self, timestamper, job_id):

        self.job_id = job_id
        self.timestamper = timestamper

        self.nc_job_id = 0
        self.hash = None
        self.height = 0
        self.version = 0
        self.prevhash = None
        self.prevhash_hex = ''
        self.prev_keystone = None
        self.second_keystone = None
        self.merkle_root = None
        self.intermediate_merkles = []
        self.curtime = 0
        self.timestamp = 0
        self.nBits = 0
        self.nonce = 0
        self.extranonce = 0

        self.target = 0

        self.broadcast_args = []

        # List of 3-tuples (extranonce, ntime, nonce)
        # registers already submitted and checked shares
        # There may be registered also invalid shares inside!
        self.submits = []

    def fill_from_job(self, job):
        self.nc_job_id = job['job_id']['data']
        self.height = job['block_index']['data']
        self.version = job['block_version']['data']
        self.prevhash = binascii.unhexlify(job['previous_block_hash']['data'])[-12:]
        self.prevhash_hex = job['previous_block_hash']['data']
        self.prev_keystone = binascii.unhexlify(job['second_previous_block_hash']['data'])[-9:]
        self.second_keystone = binascii.unhexlify(job['third_previous_block_hash']['data'])[-9:]
        self.merkle_root = binascii.unhexlify(job['merkle_root']['data'])
        self.intermediate_merkles = [
            binascii.unhexlify(job['pop_transaction_merkle_root']['data']),
            binascii.unhexlify(job['normal_transaction_merkle_root']['data']),
            binascii.unhexlify(job['intermediate_metapackage_hash']['data'])
        ]
        self.nBits = job['difficulty']['data']
        self.curtime = job['timestamp']['data']
        self.timestamp = 0
        self.nonce = 0

        difficulty = util.uint256_from_compact(self.nBits)
        self.target = self.diff_to_target(difficulty)

        self.broadcast_args = self.build_broadcast_args()

    
    def diff_to_target(self, difficulty):
        '''Converts difficulty to target'''
        max_diff = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        return max_diff // difficulty

    def register_submit(self, extranonce, ntime, nonce):
        t = (extranonce, ntime, nonce)
        if t not in self.submits:
            self.submits.append(t)
            return True
        return False

    def build_broadcast_args(self):
        job_id = self.job_id
        height = binascii.hexlify(struct.pack(">i", self.height)).decode('utf_8')
        version = binascii.hexlify(struct.pack(">h", self.version)).decode('utf_8')
        prevhash = binascii.hexlify(self.prevhash).decode('utf_8')
        prevkeystone = binascii.hexlify(self.prev_keystone).decode('utf_8')
        secondkeystone = binascii.hexlify(self.second_keystone).decode('utf_8')
        intermediate_merkles = [binascii.hexlify(x).decode('utf_8') for x in self.intermediate_merkles]
        time = binascii.hexlify(struct.pack(">i", self.curtime)).decode('utf_8')
        difficulty = binascii.hexlify(struct.pack(">i", self.nBits)).decode('utf_8')
        clean_jobs = True

        return (job_id, height, version, prevhash, prevkeystone, secondkeystone, intermediate_merkles, time, difficulty, clean_jobs)

    def check_ntime(self, ntime):
        '''Check for ntime restrictions.'''
        if ntime < self.curtime:
            return False

        if ntime > (self.timestamper.time() + 1000):
            # Be strict on ntime into the near future
            # may be unnecessary
            return False

        return True

    def serialize_header(self, merkle_root_bin, time, nonce):
        '''Serialize header for calculating block hash'''
        r  = struct.pack(">i", self.height)
        r += struct.pack(">h", self.version)
        r += self.prevhash
        r += self.prev_keystone
        r += self.second_keystone
        r += merkle_root_bin
        r += struct.pack(">i", time)
        r += struct.pack(">i", self.nBits)
        r += struct.pack(">i", nonce)
        return r

    def finalize(self, merkle_root, extranonce, timestamp, nonce):
        '''Take all parameters required to compile block candidate.
        self.is_valid() should return True then...'''

        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.nonce = nonce
        self.extranonce = extranonce
        self.hash = None

    def is_valid(self):
        self.calc_hash()
        hash_int = util.uint192_from_str_be(self.hash)
        if hash_int > self.target:
            return False
        
        mt = MerkleTree(self.intermediate_merkles)
        merkle_root_bin = mt.calculate_merkle_root(self.extranonce)
        if merkle_root_bin != self.merkle_root:
            return False    
        
        return True

    def calc_hash(self):
        if self.hash is None:
            header = self.serialize_header(self.merkle_root, self.timestamp, self.nonce)
            self.hash = vblake.getPoWHash(header)

        return self.hash
