package nodecore.miners.pow;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public class Utility {
    public static final char[] HEX_ALPHABET_ARRAY = "0123456789ABCDEF".toCharArray();

    public static boolean isInteger(String toTest) {
        if (toTest == null) {
            return false;
        }
        try {
            Integer.parseInt(toTest);
            return true;
        } catch (Exception ignored) {
            return false;
        }
    }

    public static boolean isPositiveInteger(String toTest) {
        if (toTest == null) {
            return false;
        }
        try {
            int parsed = Integer.parseInt(toTest);
            if (parsed > 0)
                return true;
        } catch (Exception ignored) {
            return false;
        }
        return false;
    }

    public static boolean isValidPort(int port) {
        return port > 0 && port < 65536;
    }

    public static boolean isHex(String toTest) {
        if (toTest == null) {
            throw new IllegalArgumentException("isHex cannot be called with a null String!");
        }


        for (char c : toTest.toCharArray()) {
            switch(c) {
                case '0':
                case '1':
                case '2':
                case '3':
                case '4':
                case '5':
                case '6':
                case '7':
                case '8':
                case '9':
                case 'a':
                case 'b':
                case 'c':
                case 'd':
                case 'e':
                case 'f':
                case 'A':
                case 'B':
                case 'C':
                case 'D':
                case 'E':
                case 'F':
                    continue;
                default:
                    return false;
            }
        }

        return true;
    }

    /**
     * Encodes the provided hexadecimal string into a byte array.
     *
     * @param s The hexadecimal string
     * @return A byte array consisting of the bytes within the hexadecimal String
     */
    public static byte[] hexToBytes(String s) {
        if (s == null) {
            throw new IllegalArgumentException("hexToBytes cannot be called with a null String!");
        }

        if (!isHex(s)) {
            throw new IllegalArgumentException("hexToBytes cannot be called with a non-hex String (called with " + s + ")!");
        }

        int len = s.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(s.charAt(i), 16) << 4)
                    + Character.digit(s.charAt(i+1), 16));
        }
        return data;
    }

    /**
     * Encodes the provided byte array into an upper-case hexadecimal string.
     *
     * @param bytes The byte array to encode
     * @return A String of the hexadecimal representation of the provided byte array
     */
    public static String bytesToHex(byte[] bytes) {
        if (bytes == null) {
            throw new IllegalArgumentException("bytesToHex cannot be called with a null byte array!");
        }

        /* Two hex characters always represent one byte */
        char[] hex = new char[bytes.length << 1];
        for (int i = 0, j = 0; i < bytes.length; i++) {
            hex[j++] = HEX_ALPHABET_ARRAY[(0xF0 & bytes[i]) >>> 4];
            hex[j++] = HEX_ALPHABET_ARRAY[(0x0F & bytes[i])];
        }
        return new String(hex);
    }

    /**
     * Converts a long to a byte[] in big-endian.
     *
     * @param input The long to convert into a byte[]
     * @return The byte[] representing the provided long
     */
    public static byte[] longToByteArray(long input) {
        return new byte[]{
                (byte) ((input & 0xFF00000000000000l) >> 56),
                (byte) ((input & 0x00FF000000000000l) >> 48),
                (byte) ((input & 0x0000FF0000000000l) >> 40),
                (byte) ((input & 0x000000FF00000000l) >> 32),
                (byte) ((input & 0x00000000FF000000l) >> 24),
                (byte) ((input & 0x0000000000FF0000l) >> 16),
                (byte) ((input & 0x000000000000FF00l) >> 8),
                (byte) ((input & 0x00000000000000FFl)),
        };
    }

    /**
     * Converts an integer to a byte[] in big-endian.
     *
     * @param input The integer to convert into a byte[]
     * @return The byte[] representing the provided integer
     */
    public static byte[] intToByteArray(int input) {
        return new byte[]{
                (byte) ((input & 0xFF000000) >> 24),
                (byte) ((input & 0x00FF0000) >> 16),
                (byte) ((input & 0x0000FF00) >> 8),
                (byte) ((input & 0x000000FF)),
        };
    }

    public static byte[] sha256(byte[] first, byte[] second) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            digest.update(first);
            digest.update(second);
            return digest.digest();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);  // Can't happen.
        }
    }
}
