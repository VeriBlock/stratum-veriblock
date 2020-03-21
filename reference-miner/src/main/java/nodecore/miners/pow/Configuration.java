// VeriBlock NodeCore
// Copyright 2017-2020 Xenios SEZC
// All rights reserved.
// https://www.veriblock.org
// Distributed under the MIT software license, see the accompanying
// file LICENSE or http://www.opensource.org/licenses/mit-license.php.

package nodecore.miners.pow;

public class Configuration {
    public int numThreadsInput;
    public String hostAndPort;
    public String username;

    public String getHost() {
        if (hostAndPort == null || hostAndPort.length() == 0) return null;

        return hostAndPort.split(":")[0];
    }

    public int getPort() {
        if (hostAndPort == null || hostAndPort.length() == 0) return -1;

        return Integer.parseInt(hostAndPort.split(":")[1]);
    }
}
