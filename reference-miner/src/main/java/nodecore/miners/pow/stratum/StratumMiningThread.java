package nodecore.miners.pow.stratum;

import nodecore.miners.pow.Utility;
import nodecore.miners.pow.VBlake;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.time.Instant;
import java.util.Arrays;
import java.util.concurrent.atomic.AtomicBoolean;

public class StratumMiningThread extends Thread {
    private static final Logger logger = LoggerFactory.getLogger(StratumMiningThread.class);

    private static final BigInteger TARGET = new BigInteger("000000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 16);
    private final Consumer<StratumJob, Long, byte[]> submitFunc;
    private boolean running = false;
    private AtomicBoolean jobUpdated = new AtomicBoolean(false);
    private long extraNonce;
    private StratumJob job;

    public void setExtraNonce(long extraNonce) {
        this.extraNonce = extraNonce;
    }

    public void setJob(StratumJob job) {
        this.job = job;
        this.jobUpdated.set(true);
    }

    StratumMiningThread(Consumer<StratumJob, Long, byte[]> submitFunc) {
        this.submitFunc = submitFunc;
    }

    @Override
    public void run() {
        running = true;

        // Await work
        while (running) {
            if (job == null) {
                try {
                    Thread.sleep(3000);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
                continue;
            }

            int timestamp = (int) Instant.now().getEpochSecond();
            ByteBuffer work = job.constructPrototype(timestamp, this.extraNonce);

            int iterationCount = 1;
            for (int nonce = Integer.MIN_VALUE; nonce < Integer.MAX_VALUE; nonce++) {
                if (!running) break;

                if (jobUpdated.get()) {
                    jobUpdated.set(false);
                    break;
                }

                // Periodically update the timestamp
                if (iterationCount == 10000) {
                    iterationCount = 0;
                    timestamp = (int) Instant.now().getEpochSecond();
                    work.putInt(52, timestamp);
                }

                work.putInt(60, nonce);
                byte[] hash = VBlake.hash(work.array());
                BigInteger hashVal = new BigInteger(1, hash);
                if (hashVal.compareTo(TARGET) < 0) {
                    logger.info("Header: {}", Utility.bytesToHex(work.array()));
                    logger.info("Found share: {}", Utility.bytesToHex(hash));
                    // Submit Share
                    this.submitFunc.accept(this.job, this.extraNonce, Arrays.copyOf(work.array(), 64));
                }

                iterationCount++;
            }
        }
    }

    public void shutdown() {
        this.running = false;
    }
}
