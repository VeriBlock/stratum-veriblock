package nodecore.miners.pow.stratum;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.veriblock.core.utilities.Utility;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

public class StratumClient {
    private final String username;
    private final OutputStream out;
    private final BufferedReader in;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private final AtomicInteger requestCounter = new AtomicInteger(0);
    private final Map<String, CompletableFuture<String>> requests = new ConcurrentHashMap<>();
    private final Gson serializer;
    private final JsonParser parser;
    private final ExecutorService executor;

    private BiConsumer<Long, Integer> subscribeHandler;
    public void setSubscribeHandler(BiConsumer<Long, Integer> subscribeHandler) {
        this.subscribeHandler = subscribeHandler;
    }

    private Consumer<StratumJob> jobHandler;
    public void setJobHandler(Consumer<StratumJob> jobHandler) {
        this.jobHandler = jobHandler;
    }

    public Integer nextRequestId() {
        return requestCounter.incrementAndGet();
    }

    public StratumClient(String username, OutputStream out, BufferedReader in) {
        this.username = username;
        this.out = out;
        this.in = in;

        this.serializer = new Gson();
        this.parser = new JsonParser();
        this.executor = Executors.newSingleThreadExecutor();
    }

    public void start() {
        running.set(true);
        executor.submit(this::run);

        CompletableFuture<String> subscribe = new CompletableFuture<>();
        subscribe.thenAccept(this::handleSubscribeResponse);

        // Send the subscribe request
        String requestId = subscribe();
        requests.put(requestId, subscribe);
    }

    public void submitShare(String jobId, long extraNonce, int timestamp, int nonce) {
        RequestCommand request = new RequestCommand();
        request.id = nextRequestId().toString();
        request.method = "mining.submit";
        request.params = new String[] {
                this.username,
                jobId,
                Utility.bytesToHex(Utility.longToByteArray(extraNonce)),
                Utility.bytesToHex(Utility.intToByteArray(timestamp)),
                Utility.bytesToHex(Utility.intToByteArray(nonce))
        };

        try {
            send(request);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void shutdown() {
        this.running.set(false);
    }

    private void run() {
        while(running.get()) {
            try {
                String message = in.readLine();
                System.out.println(message);

                JsonObject json = parser.parse(message).getAsJsonObject();
                if (json.has("method")) {
                    // Handle incoming command
                    handleRequest(json);
                } else if (json.has("result")) {
                    // Handle successful response
                    CompletableFuture<String> request = requests.get(json.get("id").getAsString());
                    if (request != null) {
                        request.complete(message);
                    }
                } else if (json.has("error")) {
                    // Handle error response
                }
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    private void send(RequestCommand request) throws IOException {
        byte[] data = String.format("%s\n", serializer.toJson(request)).getBytes(StandardCharsets.UTF_8);
        System.out.println("SENDING: " + serializer.toJson(request));
        this.out.write(data);
    }

    private String subscribe() {
        Integer requestId = nextRequestId();

        RequestCommand request = new RequestCommand();
        request.id = requestId.toString();
        request.method = "mining.subscribe";
        request.params = new String[] {};

        try {
            send(request);
        } catch (IOException e) {
            e.printStackTrace();
        }

        return requestId.toString();
    }

    private void handleSubscribeResponse(String line) {
        System.out.println("SUBSCRIBED!");
        if (subscribeHandler != null) {
            JsonArray result = parser.parse(line).getAsJsonObject().get("result").getAsJsonArray();
            subscribeHandler.accept(Long.parseLong(result.get(1).getAsString(), 16), result.get(2).getAsInt());
        }


        RequestCommand request = new RequestCommand();
        request.id = nextRequestId().toString();
        request.method = "mining.authorize";
        request.params = new String[] { this.username, ""};

        try {
            send(request);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private void handleRequest(JsonObject json) {
        if (json.get("method").getAsString().equals("mining.notify")) {
            JsonArray params = json.getAsJsonArray("params");
            StratumJob job = new StratumJob(
                    params.get(0).getAsString(),
                    Integer.parseInt(params.get(1).getAsString(), 16),
                    Short.parseShort(params.get(2).getAsString(), 16),
                    params.get(3).getAsString(),
                    params.get(4).getAsString(),
                    params.get(5).getAsString(),
                    new String[] {
                            params.get(6).getAsJsonArray().get(0).getAsString(),
                            params.get(6).getAsJsonArray().get(1).getAsString(),
                            params.get(6).getAsJsonArray().get(2).getAsString()
                    },
                    Integer.parseInt(params.get(7).getAsString(), 16),
                    Integer.parseInt(params.get(8).getAsString(), 16));

            if (jobHandler != null) {
                jobHandler.accept(job);
            }
        }
    }
}
