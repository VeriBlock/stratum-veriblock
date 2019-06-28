import struct

class ExtranonceCounter(object):
    '''Implementation of a counter producing
       unique extranonce across all pool instances.
       This is just dumb "quick&dirty" solution,
       but it can be changed at any time without breaking anything.'''

    def __init__(self, instance_id):
        if instance_id < 0 or instance_id > 31:
            raise Exception("Current ExtranonceCounter implementation needs an instance_id in <0, 31>.")

        # Last 6 most-significant bits represents instance_id
        # The rest is just an iterator of jobs.
        self.counter = instance_id << 58
        self.size = struct.calcsize('>q')

    def get_size(self):
        '''Return expected size of generated extranonce in bytes'''
        return self.size

    def get_new_bin(self):
        self.counter += 1000000
        return struct.pack('>q', self.counter)

