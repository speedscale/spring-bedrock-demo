package org.aws.springaiamazonbedrock;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.http.AbortableInputStream;
import software.amazon.awssdk.http.ExecutableHttpRequest;
import software.amazon.awssdk.http.HttpExecuteRequest;
import software.amazon.awssdk.http.HttpExecuteResponse;
import software.amazon.awssdk.http.SdkHttpClient;
import software.amazon.awssdk.http.SdkHttpResponse;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(BedrockRequestTest.Config.class)
class BedrockRequestTest {
    private static final AtomicReference<String> REQUEST = new AtomicReference<>();

    @Autowired
    private TestRestTemplate http;

    @Autowired
    private ObjectMapper json;

    @Test
    void invokesSonnet55WithoutDeprecatedTemperature() throws Exception {
        var headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        var response = http.postForEntity("/api/chat",
                new HttpEntity<>("{\"prompt\":\"How do I reset my password?\"}", headers), String.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(json.readTree(response.getBody()).path("response").asText())
                .isEqualTo("Use the password reset link.");
        var request = json.readTree(REQUEST.get());
        assertThat(request.path("inferenceConfig").has("temperature")).isFalse();
        assertThat(request.path("inferenceConfig").path("maxTokens").asInt()).isEqualTo(256);
        assertThat(request.path("messages").get(0).path("content").get(0).path("text").asText())
                .isEqualTo("How do I reset my password?");
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class Config {
        @Bean
        BedrockRuntimeClient bedrockRuntimeClient() {
            return BedrockRuntimeClient.builder().region(Region.US_EAST_1)
                    .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("test", "test")))
                    .httpClient(new SdkHttpClient() {
                        @Override
                        public ExecutableHttpRequest prepareRequest(HttpExecuteRequest request) {
                            assertThat(request.httpRequest().encodedPath())
                                    .contains("us.anthropic.claude-sonnet-5-5");
                            return new ExecutableHttpRequest() {
                                @Override
                                public HttpExecuteResponse call() throws IOException {
                                    String body = new String(request.contentStreamProvider().orElseThrow()
                                            .newStream().readAllBytes(), StandardCharsets.UTF_8);
                                    REQUEST.set(body);
                                    boolean invalid = body.contains("\"temperature\"");
                                    String result = invalid ? "{\"message\":\"temperature is deprecated\"}" : """
                                            {"output":{"message":{"role":"assistant","content":[{"text":"Use the password reset link."}]}},
                                             "stopReason":"end_turn","usage":{"inputTokens":10,"outputTokens":5,"totalTokens":15},
                                             "metrics":{"latencyMs":1}}
                                            """;
                                    return HttpExecuteResponse.builder()
                                            .response(SdkHttpResponse.builder().statusCode(invalid ? 400 : 200)
                                                    .putHeader("Content-Type", "application/json").build())
                                            .responseBody(AbortableInputStream.create(new ByteArrayInputStream(
                                                    result.getBytes(StandardCharsets.UTF_8)))).build();
                                }

                                @Override
                                public void abort() {}
                            };
                        }

                        @Override
                        public void close() {}
                    }).build();
        }
    }
}
