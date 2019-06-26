// VeriBlock PoW CPU Miner
// Copyright 2017-2019 Xenios SEZC
// All rights reserved.
// https://www.veriblock.org
// Distributed under the MIT software license, see the accompanying
// file LICENSE or http://www.opensource.org/licenses/mit-license.php.

package nodecore.miners.pow;
import nodecore.api.ucp.commands.UCPClientCommand;
import nodecore.api.ucp.commands.UCPIncomingCommandParser;
import nodecore.api.ucp.commands.client.*;
import nodecore.api.ucp.commands.server.MiningAuth;
import nodecore.api.ucp.commands.server.MiningSubmit;
import nodecore.api.ucp.commands.server.MiningSubscribe;
import nodecore.miners.pow.stratum.JobManager;
import nodecore.miners.pow.stratum.StratumClient;
import org.veriblock.core.SharedConstants;
import org.veriblock.core.types.Pair;
import org.veriblock.core.utilities.AddressUtility;
import org.veriblock.core.utilities.Utility;

import java.io.*;
import java.net.InetAddress;
import java.net.Socket;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.Properties;
import java.util.Random;
import java.util.Scanner;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;

public class MainClass {
    private static final int MAX_PORT_NUM = 65335;
    private static final int MIN_PORT_NUM = 0;

    private static final Random random = new Random();

    public static void main(String... args) {
        System.out.print(SharedConstants.LICENSE);

        AtomicBoolean running = new AtomicBoolean(true);
        Scanner scan = new Scanner(System.in);

        System.out.println("===[ VeriBlock Proof-of-Work (PoW) CPU Miner ]===");
        System.out.println("https://www.veriblock.org/");
        System.out.println("Please ensure that you have the credentials for a pool to connect to, or a local NodeCore instance is running.");
        System.out.println("If running a local NodeCore instance, then use the NodeCore CLI to run the command: startpool");

        int numThreads = 0;
        String hostAndPort = null;
        String address = null;

        InputValues input = GetInputFromFile();
        if (input == null)
        {
            System.out.println(String.format("Config File '%1$s' does not exist. Please enter the following values:", PROPERTY_FILE));

            //get from UI
            int iProcessorCount = Runtime.getRuntime().availableProcessors();

            System.out.println(String.format("How many threads would you like to mine on? Default=1, Maximum suggested=%1$s", iProcessorCount));
            String numThreadsInput = scan.nextLine();
            if (numThreadsInput.equals(""))
            {
                numThreadsInput = "1";
                System.out.println("Using default = 1");
            }
            while (!Utility.isPositiveInteger(numThreadsInput)) {
                System.out.println("Please enter an integer for the number of threads (" + numThreadsInput +
                        " was entered which is not a positive integer)");
                numThreadsInput = scan.nextLine();

                if (numThreadsInput.equals(""))
                {
                    numThreadsInput = "1";
                    System.out.println("Using default = 1");
                }
            }

            numThreads = Integer.parseInt(numThreadsInput);

            System.out.println("What host:port would you like to connect to for mining? (Use the port for UPC. Default 127.0.0.1:8501)");
            hostAndPort = scan.nextLine();
            if (hostAndPort.equals(""))
            {
                hostAndPort = "127.0.0.1:8501";
                System.out.println("Using default = 127.0.0.1:8501");
            }

            Pair<String, Integer> remoteHost = getHostAndPortFromInput(hostAndPort);
            while (!isValidAddressPortPair(hostAndPort) || remoteHost.getSecond() == 8500) {
                if (remoteHost.getSecond() == 8500) {
                    System.out.println("It appears you are trying to mine to a pool interface port!");
                    System.out.println("You probably want to use port 8501 instead. Would you like to switch");
                    System.out.println("To the recommended port (8501) instead? (yes/no)");
                    String line = scan.nextLine();
                    if (line.equalsIgnoreCase("y") || line.equalsIgnoreCase("yes")) {
                        System.out.println("Switching to port 8501...");
                        hostAndPort = remoteHost.getFirst() + ":8501";
                    } else {
                        System.out.println("Leaving port 8500...");
                        hostAndPort = remoteHost.getFirst() + ":8500";
                    }

                } else {
                    System.out.println("Please enter a valid host:port combination, such as `127.0.0.1:8501`!");
                    hostAndPort = scan.nextLine();

                    if (hostAndPort.equals("")) {
                        hostAndPort = "127.0.0.1:8501";
                        System.out.println("Using default = 127.0.0.1:8501");
                    }
                }

                remoteHost = getHostAndPortFromInput(hostAndPort);
            }

            System.out.println("What username/address would you like to mine to?");
            address = scan.nextLine();
            while (!AddressUtility.isValidStandardOrMultisigAddress(address)) {
                System.out.println("The username (" + address + ") you entered is not a valid VeriBlock address; are you mining to a solo pool? (yes/no)");
                String confirmation = scan.nextLine();
                if (confirmation.equalsIgnoreCase("yes") || confirmation.equalsIgnoreCase("y")) {
                    break;
                } else {
                    System.out.println("Enter a valid VeriBlock address (starts with a 'V'):");
                    address = scan.nextLine();
                }
            }
        }
        else
        {
            //get from file
            System.out.println(String.format("File '%1$s' exists, get values from config:", PROPERTY_FILE));
            numThreads = input.numThreadsInput;
            hostAndPort = input.hostAndPort;
            address = input.address;
            System.out.println(String.format("Number of threads=%1$s", numThreads));
            System.out.println(String.format("Host and Port=%1$s", hostAndPort));
            System.out.println(String.format("Address=%1$s", address));
        }

        Pair<String, Integer> remoteHost = getHostAndPortFromInput(hostAndPort);

        String hostName = remoteHost.getFirst();
        int remotePort = remoteHost.getSecond();
        ShareRepo shareRepo = null;
        MinerThreadManager minerThreadManager = null;

        Thread gateThread = null;
        do {
            try {
                System.out.println("Attempting to connect to " + hostName + ":" + remotePort);

                try (Socket remoteSocket = new Socket(hostName, remotePort);
                    BufferedReader in = new BufferedReader(new InputStreamReader(remoteSocket.getInputStream()))) {
                    CountDownLatch gate = new CountDownLatch(1);

                    if (gateThread != null) {
                        Runtime.getRuntime().removeShutdownHook(gateThread);
                    }
                    gateThread = new Thread(() -> {
                        running.set(false);
                        gate.countDown();
                    });
                    Runtime.getRuntime().addShutdownHook(gateThread);

                    StratumClient client = new StratumClient(address, remoteSocket.getOutputStream(), in);
                    JobManager manager = new JobManager(client);

                    manager.start(numThreads);
                    client.start();

                    gate.await();

                    manager.shutdown();
                    client.shutdown();
                }
            } catch (IOException e) {
                System.out.println("The Reference PoW miner is unable to connect to the specified remote mining host!");
                System.out.println("Make sure that NodeCore is running on host:port " + hostAndPort + ", and that a pool is started (run the command startpool)");
                e.printStackTrace();
                try { Thread.sleep(1000); } catch (Exception ignored) { }
            } catch (Exception e) {
                e.printStackTrace();
            }
        } while (running.get());
    }

    private static final String PROPERTY_FILE = "nodecore_miner_pow.properties";

    private static InputValues GetInputFromFile()
    {
        //check if file exits
        boolean exists = (new File(PROPERTY_FILE)).exists();
        if (!exists)
        {
            return null;
        }

        InputValues data = new InputValues();

        Properties prop = new Properties();
        InputStream input = null;

        try {

            input = new FileInputStream(PROPERTY_FILE);

            // load a properties file
            prop.load(input);

            // get the property value and print it out
            data.numThreadsInput = Integer.parseInt( prop.getProperty("miner.threadcount"));
            data.address =  prop.getProperty("miner.address");
            data.hostAndPort =  prop.getProperty("miner.host");

        } catch (Exception ex) {
            ex.printStackTrace();
        } finally {
            if (input != null) {
                try {
                    input.close();
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }

        return data;
    }
    private static Pair<String, Integer> getHostAndPortFromInput(String input) {
        if (input == null) {
            throw new IllegalArgumentException("getHostAndPortFromInput cannot be called with a null input!");
        }

        String[] parts = input.split(":");
        if (parts.length != 2) {
            throw new IllegalArgumentException("getHostNameFromInput" + " cannot be called with an input which doesn't" +
                    " have a host:port combo.");
        }

        String host = parts[0];
        int port = Integer.parseInt(parts[1]);

        if (port > MAX_PORT_NUM || port < MIN_PORT_NUM) {
            throw new IllegalArgumentException("getHostNameFromInput " + " cannot be called with an out-of-range port (" +
                    port + ")!");
        }

        return new Pair<>(host, port);
    }

    private static boolean isValidAddressPortPair(String pair) {
        String[] addressSections = pair.split(":");
        if (addressSections.length != 2) {
            System.out.println("The supplied address:port pair \"" + pair + "\" is not valid! Please format the pool" +
                    "IP as host:port, such as 127.0.0.1:8501!");
            return false;
        }

        String host = addressSections[0];
        try {
            InetAddress.getByName(host);
        } catch (UnknownHostException | SecurityException hostException) {
            System.out.println("Warning: Could not lookup host '" + host + "'");
        }

        if (!Utility.isInteger(addressSections[1])) {
            System.out.println("The provided port (" + addressSections[1] + ") is not valid!");
            return false;
        }

        if (!Utility.isValidPort(Integer.parseInt(addressSections[1]))) {
            System.out.println("The provided port (" + addressSections[1] + ") is not valid!");
            return false;
        }

        return true;
    }
}
