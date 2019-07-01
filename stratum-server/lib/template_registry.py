import weakref
import binascii
import struct

from twisted.internet import defer

import stratum.logger
log = stratum.logger.get_logger('template_registry')

from mining.interfaces import Interfaces
from lib.exceptions import SubmitException
from lib.extranonce_counter import ExtranonceCounter
from lib.merkletree import MerkleTree
import lib.util as util
import vblake

class JobIdGenerator(object):
    '''Generate pseudo-unique job_id. It does not need to be absolutely unique,
    because pool sends "clean_jobs" flag to clients and they should drop all previous jobs.'''
    counter = 0

    @classmethod
    def get_new_id(cls):
        cls.counter += 1
        if cls.counter % 0xffff == 0:
            cls.counter = 1
        return "%x" % cls.counter

class TemplateRegistry(object):
    '''Implements the main logic of the pool. Keep track
    on valid block templates, provide internal interface for stratum
    service and implements block validation and submits.'''

    def __init__(self, protocol, instance_id,
                 on_template_callback, on_block_callback, on_difficulty_callback):
        self.prevhashes = {}
        self.jobs = weakref.WeakValueDictionary()

        self.extranonce_counter = ExtranonceCounter(instance_id)
        self.extranonce_size = 8
        
        self.protocol = protocol
        self.on_block_callback = on_block_callback
        self.on_template_callback = on_template_callback
        self.on_difficulty_callback = on_difficulty_callback

        self.last_block = None
        self.update_in_progress = False
        self.last_update = None

    def get_new_extranonce(self):
        '''Generates unique extranonce (e.g. for newly
        subscribed connection.'''
        return self.extranonce_counter.get_new_bin()

    def get_last_broadcast_args(self):
        '''Returns arguments for mining.notify
        from last known template.'''
        return self.last_block.broadcast_args

    def add_template(self, block):
        '''Adds new template to the registry.
        It also clean up templates which should
        not be used anymore.'''

        prevhash = block.prevhash_hex
        
        previous_hash_keys = list(self.prevhashes)
        if prevhash in previous_hash_keys:
            new_block = False
        else:
            new_block = True
            self.prevhashes[prevhash] = []

        # Blocks sorted by prevhash, so it's easy to drop
        # them on blockchain update
        self.prevhashes[prevhash].append(block)

        # Weak reference for fast lookup using job_id
        self.jobs[block.job_id] = block

        # Use this template for every new request
        self.last_block = block

        # Drop templates of obsolete blocks
        for ph in previous_hash_keys:
            if ph != prevhash:
                del self.prevhashes[ph]

        log.info("New template for %s" % prevhash)

        if new_block:
            # Tell the system about new block
            # It is mostly important for share manager
            self.on_difficulty_callback(block.difficulty)
            self.on_block_callback(prevhash)

        # Everything is ready, let's broadcast jobs!
        self.on_template_callback(new_block)

    def diff_to_target(self, difficulty):
        '''Converts difficulty to target'''
        # Max Value / Difficulty = Target
        diff1 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        return diff1 / difficulty

    def get_job(self, job_id):
        '''For given job_id returns BlockTemplate instance or None'''
        try:
            j = self.jobs[job_id]
        except:
            log.info("Job id '%s' not found" % job_id)
            return None

        # Now we have to check if job is still valid.
        # Unfortunately weak references are not bulletproof and
        # old reference can be found until next run of garbage collector.
        if j.prevhash_hex not in self.prevhashes:
            log.info("Prevhash of job '%s' is unknown" % job_id)
            return None

        if j not in self.prevhashes[j.prevhash_hex]:
            log.info("Job %s is unknown" % job_id)
            return None

        return j

    def submit_share(self, job_id, worker_name, extranonce, ntime, nonce, difficulty):
        '''Check parameters and finalize block template. If it leads
           to valid block candidate, asynchronously submits the block
           back to the network.

            - job_id, extranonce, ntime, nonce - in hex form sent by the client
            - difficulty - decimal number from session, again no checks performed
            - submitblock_callback - reference to method which receive result of submitblock()
        '''

        # Check if extranonce looks correctly. extranonce is in hex form...
        if len(extranonce) != self.extranonce_size * 2:
            raise SubmitException("Incorrect size of extranonce. Expected 16 chars")

        # Check for job
        job = self.get_job(job_id)
        if job == None:
            raise SubmitException("Job '%s' not found" % job_id)

        # Check if ntime looks correct
        if len(ntime) != 8:
            raise SubmitException("Incorrect size of ntime. Expected 8 chars")

        ntime_int = util.hex_to_int32(ntime)
        if not job.check_ntime(ntime_int):
            raise SubmitException("Ntime out of range")

        # Check nonce
        if len(nonce) != 8:
            raise SubmitException("Incorrect size of nonce. Expected 8 chars")

        # Convert from hex to binary
        extranonce_int = util.hex_to_int64(extranonce)
        nonce_int = util.hex_to_int32(nonce)

        # Check for duplicated submit
        if not job.register_submit(extranonce_int, ntime_int, nonce_int):
            log.info("Duplicate from %s, (%s %s %s %s)" % \
                    (worker_name, extranonce_int, ntime_int, nonce_int))
            raise SubmitException("Duplicate share")

        # Now let's do the hard work!
        # ---------------------------

        # 1. Calculate merkle root
        mt = MerkleTree(job.intermediate_merkles)
        merkle_root_bin = mt.calculate_merkle_root(extranonce_int)

        # 2. Serialize header with given merkle, ntime and nonce
        header_bin = job.serialize_header(merkle_root_bin, ntime_int, nonce_int)

        # 3. Compare header with target of the user
        hash_bin = vblake.getPoWHash(header_bin)
        hash_int = util.uint192_from_str_be(hash_bin)
        block_hash_hex = "%048x" % hash_int
        header_hex = binascii.hexlify(header_bin)

        target_user = self.diff_to_target(difficulty)
        if hash_int > target_user:
            raise SubmitException("Share is above target")

        # 4. Compare hash with target of the network
        if hash_int < job.target:
            # Yay! It is block candidate!
            log.info("We found a block candidate! %s" % block_hash_hex)

            # 5. Finalize and serialize block object
            job.finalize(merkle_root_bin, extranonce_int, ntime_int, nonce_int)

            if not job.is_valid():
                # Should not happen
                log.error("Final job validation failed!")

            # 6. Submit block to the network
            on_submit = self.protocol.submit_share(job.nc_job_id, extranonce_int, ntime_int, nonce_int)

            return (header_hex, block_hash_hex, on_submit)

        return (header_hex, block_hash_hex, None)
