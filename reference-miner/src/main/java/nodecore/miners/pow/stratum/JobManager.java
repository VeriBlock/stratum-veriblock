package nodecore.miners.pow.stratum;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;

public class JobManager {
    private static final Logger logger = LoggerFactory.getLogger(JobManager.class);
    private final StratumClient client;

    private long extraNonce;

    private final List<StratumMiningThread> workers = new ArrayList<>();

    public JobManager(StratumClient client) {
        this.client = client;
        this.client.setSubscribeHandler(this::onSubscribed);
        this.client.setJobHandler(this::onJob);
        this.client.setDifficultyChangedHandler(this::onDifficultyChanged);
    }

    public void start(int workerCount) throws InterruptedException {
        resetWorkers();

        logger.info("Provisioning {} workers", workerCount);
        synchronized (workers) {
            for (int i = 0; i < workerCount; i++) {
                StratumMiningThread worker = new StratumMiningThread(this::onShareFound);
                workers.add(worker);
            }
        }
    }

    public void shutdown() {
        resetWorkers();
    }

    private void onSubscribed(long extraNonce, int size) {
        this.extraNonce = extraNonce;
        synchronized (workers) {
            for (int i = 0; i < workers.size(); i++) {
                logger.info("Starting worker");
                workers.get(i).setExtraNonce(extraNonce + (i * 10));
                workers.get(i).start();
            }
        }
    }

    private void onJob(StratumJob job) {
        synchronized (workers) {
            for (StratumMiningThread worker : workers) {
                worker.setJob(job);
            }
        }
    }

    private void onDifficultyChanged(BigInteger difficulty) {
        synchronized (workers) {
            for (StratumMiningThread worker : workers) {
                worker.setDifficulty(difficulty);
            }
        }
    }

    private void onShareFound(StratumJob job, Long extraNonce, byte[] solution) {
        ByteBuffer buffer = ByteBuffer.wrap(solution);

        client.submitShare(job.jobId, extraNonce, buffer.getInt(52), buffer.getInt(60));
    }

    private void resetWorkers() {
        synchronized (workers) {
            if (workers.size() > 0) {
                for (StratumMiningThread worker : workers) {
                    worker.shutdown();
                }
            }

            workers.clear();
        }
    }
}
