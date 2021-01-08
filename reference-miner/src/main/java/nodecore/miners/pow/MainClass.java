// VeriBlock PoW CPU Miner
// Copyright 2017-2021 Xenios SEZC
// All rights reserved.
// https://www.veriblock.org
// Distributed under the MIT software license, see the accompanying
// file LICENSE or http://www.opensource.org/licenses/mit-license.php.

package nodecore.miners.pow;
import nodecore.miners.pow.stratum.JobManager;
import nodecore.miners.pow.stratum.StratumClient;

import java.io.*;
import java.net.InetAddress;
import java.net.Socket;
import java.net.UnknownHostException;
import java.util.Properties;
import java.util.Scanner;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;

public class MainClass {
    public static void main(String... args) {
        AtomicBoolean running = new AtomicBoolean(true);

        Configuration configuration = getConfiguredProperties();
        if (configuration == null)
        {
            configuration = getConfigurationFromUserInput();
        }

        System.out.println(String.format("Number of threads=%1$s", configuration.numThreadsInput));
        System.out.println(String.format("Host and Port=%1$s", configuration.hostAndPort));
        System.out.println(String.format("Address=%1$s", configuration.username));

        Thread gateThread = null;
        do {
            try {
                try (Socket remoteSocket = new Socket(configuration.getHost(), configuration.getPort());
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

                    StratumClient client = new StratumClient(configuration.username, remoteSocket.getOutputStream(), in);
                    JobManager manager = new JobManager(client);

                    manager.start(configuration.numThreadsInput);
                    client.start();

                    gate.await();

                    manager.shutdown();
                    client.shutdown();
                }
            } catch (IOException e) {
                System.out.println("The Reference PoW miner is unable to connect to the specified remote mining host!");
                e.printStackTrace();
                try { Thread.sleep(1000); } catch (Exception ignored) { }
            } catch (Exception e) {
                e.printStackTrace();
            }
        } while (running.get());
    }

    private static final String PROPERTY_FILE = "app.properties";

    private static Configuration getConfiguredProperties() {
        //check if file exits
        boolean exists = (new File(PROPERTY_FILE)).exists();
        if (!exists)
        {
            return null;
        }

        Configuration data = new Configuration();

        Properties prop = new Properties();
        InputStream input = null;

        try {

            input = new FileInputStream(PROPERTY_FILE);

            // load a properties file
            prop.load(input);

            // get the property value and print it out
            data.numThreadsInput = Integer.parseInt( prop.getProperty("miner.threadcount"));
            data.username =  prop.getProperty("miner.username");
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

    private static Configuration getConfigurationFromUserInput() {
        Scanner scan = new Scanner(System.in);
        Configuration config = new Configuration();

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

        config.numThreadsInput = Integer.parseInt(numThreadsInput);

        while (!isValidAddressPortPair(config.hostAndPort)) {
            System.out.println("Please enter the host:port to connect to, (Default: `127.0.0.1:3333`)");
            config.hostAndPort = scan.nextLine();

            if (config.hostAndPort.equals("")) {
                config.hostAndPort = "127.0.0.1:8501";
                System.out.println("Using default = 127.0.0.1:8501");
            }
        }

        System.out.println("Please enter a username");
        config.username = scan.nextLine();

        return config;
    }

    private static boolean isValidAddressPortPair(String pair) {
        if (pair == null || pair.length() == 0) return false;

        String[] addressSections = pair.split(":");
        if (addressSections.length != 2) {
            System.out.println("The supplied username:port pair \"" + pair + "\" is not valid! Please format the pool" +
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
