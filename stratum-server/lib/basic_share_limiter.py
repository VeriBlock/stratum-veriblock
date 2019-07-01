import time

from twisted.internet import defer
from stratum import settings
import stratum.logger as logger

log = logger.get_logger('BasicShareLimiter')

# import DBInterface
# dbi = DBInterface.DBInterface()
# dbi.clear_worker_diff()

''' This is just a customized ring buffer '''
class SpeedBuffer:
    def __init__(self, size_max):
        self.max = size_max
        self.data = []
        self.cur = 0

    def append(self, x):
        self.data.append(x)
        self.cur += 1
        if len(self.data) == self.max:
            self.cur = 0
            self.__class__ = SpeedBufferFull

    def avg(self):
        return sum(self.data) / self.cur

    def pos(self):
        return self.cur

    def clear(self):
        self.data = []
        self.cur = 0

    def size(self):
        return self.cur

class SpeedBufferFull:
    def __init__(self, n):
        raise "you should use SpeedBuffer"

    def append(self, x):
        self.data[self.cur] = x
        self.cur = (self.cur + 1) % self.max

    def avg(self):
        return sum(self.data) / self.max

    def pos(self):
        return self.cur

    def clear(self):
        self.data = []
        self.cur = 0
        self.__class__ = SpeedBuffer

    def size(self):
        return self.max

class BasicShareLimiter(object):
    def __init__(self):
        self.worker_stats = {}
        self.target = settings.VDIFF_TARGET_TIME
        self.retarget = settings.VDIFF_RETARGET_TIME
        self.variance = self.target * (float(settings.VDIFF_VARIANCE_PERCENT) / float(100))
        self.tmin = self.target - self.variance
        self.tmax = self.target + self.variance
        self.buffersize = self.retarget / self.target * 4

        self.network_diff = settings.VDIFF_MAX_TARGET

        # self.litecoin = {}
        # TODO: trim the hash of inactive workers

    def update_network_difficulty(self, difficulty):
        # Update the network difficulty
        self.network_diff = difficulty

    def calc_ddiff(current_difficulty, target, avg):
        # Figure out our Delta-Diff
        if settings.VDIFF_FLOAT:
            ddiff = float((float(current_difficulty) * (float(self.target) / float(avg))) - current_difficulty)
        else:
            ddiff = int((float(current_difficulty) * (float(self.target) / float(avg))) - current_difficulty)

        return ddiff

    def submit(self, connection_ref, job_id, current_difficulty, timestamp, worker_name):
        ts = int(timestamp)

        # Init the stats for this worker if it isn't set.
        if worker_name not in self.worker_stats: # or self.worker_stats[worker_name]['last_ts'] < ts - settings.DB_USERCACHE_TIME :
            self.worker_stats[worker_name] = {'last_rtc': (ts - self.retarget / 2), 'last_ts': ts, 'buffer': SpeedBuffer(self.buffersize) }
            # dbi.update_worker_diff(worker_name, settings.POOL_TARGET)
            return

        # Standard share update of data
        self.worker_stats[worker_name]['buffer'].append(ts - self.worker_stats[worker_name]['last_ts'])
        self.worker_stats[worker_name]['last_ts'] = ts

        # Do We retarget? If not, we're done.
        if ts - self.worker_stats[worker_name]['last_rtc'] < self.retarget and self.worker_stats[worker_name]['buffer'].size() > 0:
            return

        # Set up and log our check
        self.worker_stats[worker_name]['last_rtc'] = ts
        avg = self.worker_stats[worker_name]['buffer'].avg()
        log.debug("Checking Retarget for %s (%i) avg. %i target %i+-%i" % (worker_name, current_difficulty, avg,
                self.target, self.variance))

        if avg < 1:
            log.warning("Reseting avg = 1 since it's SOOO low")
            avg = 1

        if avg > self.tmax:
            # For fractional -0.1 ddiff's just drop by 1
            if settings.VDIFF_X2_TYPE:
                ddiff = 0.5
                # Don't drop below POOL_TARGET
                if (ddiff * current_difficulty) < settings.VDIFF_MIN_TARGET:
                    ddiff = settings.VDIFF_MIN_TARGET / current_difficulty
            else:
                ddiff = BasicShareLimiter.calc_ddiff(current_difficulty, self.target, avg)
                if ddiff > -settings.VDIFF_MIN_CHANGE:
                    ddiff = -settings.VDIFF_MIN_CHANGE
                # Don't drop below POOL_TARGET
                if (ddiff + current_difficulty) < settings.VDIFF_MIN_TARGET:
                    ddiff = settings.VDIFF_MIN_TARGET - current_difficulty
        elif avg < self.tmin:
            # For fractional 0.1 ddiff's just up by 1
            if settings.VDIFF_X2_TYPE:
                ddiff = 2
                diff_max = min([settings.VDIFF_MAX_TARGET, self.network_diff])

                if (ddiff * current_difficulty) > diff_max:
                    ddiff = diff_max / current_difficulty
            else:
                ddiff = BasicShareLimiter.calc_ddiff(current_difficulty, self.target, avg)
                if ddiff < settings.VDIFF_MIN_CHANGE:
                   ddiff = settings.VDIFF_MIN_CHANGE

                diff_max = min([settings.VDIFF_MAX_TARGET, self.network_diff])

                if (ddiff + current_difficulty) > diff_max:
                    ddiff = diff_max - current_difficulty

        else:  # If we are here, then we should not be retargeting.
            return

        # At this point we are retargeting this worker
        if settings.VDIFF_X2_TYPE:
            new_diff = current_difficulty * ddiff
        else:
            new_diff = current_difficulty + ddiff
        log.debug("Retarget for %s %i old: %i new: %i" % (worker_name, ddiff, current_difficulty, new_diff))

        self.worker_stats[worker_name]['buffer'].clear()

        # TODO: Evaluate
        session = connection_ref().get_session()
        session['difficulty'] = new_diff
        connection_ref().rpc('mining.set_difficulty', [str(new_diff), ], is_notification=True)
        # dbi.update_worker_diff(worker_name, new_diff)
