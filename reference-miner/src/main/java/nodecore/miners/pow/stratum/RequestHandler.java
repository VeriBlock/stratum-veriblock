package nodecore.miners.pow.stratum;


import com.google.gson.Gson;

import java.util.Map;

public class RequestHandler {
    private final Gson parser;

    public RequestHandler() {
        parser = new Gson();
    }

    public void handle(String line) {
        Map map = parser.fromJson(line, Map.class);
        if (map.containsKey("method")) {
            RequestCommand command = parser.fromJson(line, RequestCommand.class);
            System.out.println(command.method);
        }
    }
}
