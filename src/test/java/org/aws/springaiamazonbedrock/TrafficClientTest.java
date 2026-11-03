package org.aws.springaiamazonbedrock;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import static org.assertj.core.api.Assertions.assertThat;

class TrafficClientTest {
    @TempDir
    Path temporary;

    private final List<String> requests = Collections.synchronizedList(new ArrayList<>());
    private final List<String> runIds = Collections.synchronizedList(new ArrayList<>());
    private HttpServer server;
    private volatile boolean unavailable;

    @BeforeEach
    void startServer() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            String request = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            requests.add(exchange.getRequestMethod() + " " + exchange.getRequestURI());
            runIds.add(exchange.getRequestHeaders().getFirst("X-Demo-Run"));
            int status = unavailable ? 503 : request.contains("\"prompt\":\"\"") ? 400 : 200;
            byte[] body = "{}".getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(status, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.start();
    }

    @AfterEach
    void stopServer() {
        server.stop(0);
    }

    private Process client(int count) throws IOException {
        return new ProcessBuilder("bash", "scripts/traffic-client.sh", "--base-url",
                "http://127.0.0.1:" + server.getAddress().getPort(), "--count", Integer.toString(count),
                "--interval", "0", "--timeout", "2", "--output", temporary.resolve("run.json").toString())
                .redirectErrorStream(true).redirectOutput(temporary.resolve("client.log").toFile()).start();
    }

    private int finish(Process process) throws InterruptedException {
        try {
            assertThat(process.waitFor(10, TimeUnit.SECONDS)).isTrue();
            return process.exitValue();
        } finally {
            process.destroyForcibly();
        }
    }

    private JsonNode summary() throws IOException {
        return new ObjectMapper().readTree(temporary.resolve("run.json").toFile());
    }

    @Test
    void sendsOnlyTheRequestedMixWithOneCorrelationId() throws Exception {
        assertThat(finish(client(7))).isZero();
        assertThat(requests).hasSize(7);
        assertThat(requests).contains("GET /actuator/health");
        assertThat(summary().path("passed").asInt()).isEqualTo(7);
        assertThat(summary().path("bedrock_chat_attempts").asInt()).isEqualTo(4);
        assertThat(summary().path("statuses").path("400").asInt()).isEqualTo(2);
        assertThat(summary().path("failures")).isEmpty();
        String runId = summary().path("run_id").asText();
        assertThat(runIds).allMatch(runId::equals);
    }

    @Test
    void stopsOnAnUnexpectedStatusWithoutRetrying() throws Exception {
        unavailable = true;
        assertThat(finish(client(8))).isEqualTo(1);
        assertThat(requests).hasSize(1);
        assertThat(summary().path("passed").asInt()).isZero();
        assertThat(summary().path("failures")).hasSize(1);
    }

    @Test
    void rejectsAnInvalidCountWithoutSendingRequests() throws Exception {
        assertThat(finish(client(0))).isEqualTo(2);
        assertThat(requests).isEmpty();
    }
}
