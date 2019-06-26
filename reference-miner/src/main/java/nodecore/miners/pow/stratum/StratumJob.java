package nodecore.miners.pow.stratum;

import nodecore.miners.pow.Utility;

import java.nio.ByteBuffer;

public class StratumJob {
    public final String jobId;
    public final int height;
    public final short version;
    public final String previousHash;
    public final String previousKeystone;
    public final String secondPreviousKeystone;
    public final String[] intermediateMerkles;
    public final int time;
    public final int difficulty;

    public StratumJob(String jobId, int height, short version, String previousHash, String previousKeystone, String secondPreviousKeystone,
                      String[] intermediateMerkles, int time, int difficulty) {
        this.jobId = jobId;
        this.height = height;
        this.version = version;
        this.previousHash = previousHash;
        this.previousKeystone = previousKeystone;
        this.secondPreviousKeystone = secondPreviousKeystone;
        this.intermediateMerkles = intermediateMerkles;
        this.time = time;
        this.difficulty = difficulty;
    }

    public ByteBuffer constructPrototype(int timestamp, long extraNonce) {
        // Calculate Merkle Root
        byte[] merkleRoot = calculateMerkleRoot(extraNonce);

        ByteBuffer buffer = ByteBuffer.allocate(64);
        buffer.putInt(height);
        buffer.putShort(version);
        buffer.put(Utility.hexToBytes(previousHash));
        buffer.put(Utility.hexToBytes(previousKeystone));
        buffer.put(Utility.hexToBytes(secondPreviousKeystone));
        buffer.put(merkleRoot);
        buffer.putInt(timestamp);
        buffer.putInt(difficulty);

        return buffer;
    }

    private byte[] calculateMerkleRoot(long extraNonce) {
        byte[] txRoot = Utility.sha256(Utility.hexToBytes(intermediateMerkles[0]), Utility.hexToBytes(intermediateMerkles[1]));
        byte[] metapackage = Utility.sha256(Utility.hexToBytes(intermediateMerkles[2]), Utility.longToByteArray(extraNonce));

        byte[] merkleRoot = Utility.sha256(metapackage, txRoot);
        byte[] trimmed = new byte[16];
        System.arraycopy(merkleRoot, 0, trimmed, 0, trimmed.length);

        return trimmed;
    }
}
