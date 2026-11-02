package org.aws.springaiamazonbedrock;

import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.ArgumentCaptor;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.MessageType;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.model.Generation;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.yaml.snakeyaml.Yaml;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "spring.ai.model.chat=none")
class ChatApiTest {
    @Autowired
    private TestRestTemplate http;

    @Autowired
    private ObjectMapper json;

    @MockitoBean
    private ChatModel model;

    @Test
    void sendsValidatedPromptToModelAndReturnsItsText() throws Exception {
        when(model.call(any(Prompt.class))).thenReturn(new ChatResponse(
                List.of(new Generation(new AssistantMessage("Use the password reset link.")))));

        var response = post("{\"prompt\":\"How do I reset my password?\"}");

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(json.readTree(response.getBody())).isEqualTo(
                json.readTree("{\"response\":\"Use the password reset link.\"}"));
        var prompt = ArgumentCaptor.forClass(Prompt.class);
        verify(model).call(prompt.capture());
        assertThat(prompt.getValue().getInstructions()).hasSize(2);
        assertThat(prompt.getValue().getInstructions().getFirst().getMessageType()).isEqualTo(MessageType.SYSTEM);
        assertThat(prompt.getValue().getInstructions().getLast().getText()).isEqualTo("How do I reset my password?");
        assertContractResponse("200", response.getBody());
    }

    @ParameterizedTest
    @ValueSource(strings = {"{}", "{\"prompt\":123}", "{\"prompt\":true}", "{\"prompt\":null}", "{\"prompt\":\"\"}",
            "{\"prompt\":\"   \"}", "{", "null", "{\"prompt\":\"hello\",\"history\":[]}"})
    void rejectsInvalidRequestsBeforeCallingBedrock(String body) throws Exception {
        var response = post(body);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertContractResponse("400", response.getBody());
        verifyNoInteractions(model);
    }

    @Test
    void rejectsOversizedPromptBeforeCallingBedrock() throws Exception {
        var response = post(json.writeValueAsString(Map.of("prompt", "x".repeat(4001))));
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        verifyNoInteractions(model);
    }

    @Test
    void acceptsPromptAtMaximumLength() throws Exception {
        when(model.call(any(Prompt.class))).thenReturn(new ChatResponse(
                List.of(new Generation(new AssistantMessage("ok")))));
        var response = post(json.writeValueAsString(Map.of("prompt", "x".repeat(4000))));
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
    }

    @Test
    void returnsDocumentedFailureWithoutLeakingUpstreamDetails() throws Exception {
        when(model.call(any(Prompt.class))).thenThrow(new IllegalStateException("private upstream detail"));
        var response = post("{\"prompt\":\"hello\"}");
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
        assertThat(response.getBody()).doesNotContain("private upstream detail");
        assertContractResponse("503", response.getBody());
    }

    @Test
    void rejectsEmptyModelOutput() {
        when(model.call(any(Prompt.class))).thenReturn(new ChatResponse(
                List.of(new Generation(new AssistantMessage(" ")))));
        assertThat(post("{\"prompt\":\"hello\"}").getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
    }

    @Test
    void healthAndProbesDoNotCallBedrock() throws Exception {
        for (String path : List.of("/actuator/health", "/actuator/health/liveness", "/actuator/health/readiness")) {
            var response = http.getForEntity(path, String.class);
            assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
            assertThat(json.readTree(response.getBody()).path("status").asText()).isEqualTo("UP");
        }
        verifyNoInteractions(model);
    }

    @Test
    void servesContractAndRemovesTemperatureAndRagRoutes() {
        var contract = http.getForEntity("/openapi.yaml", String.class);
        assertThat(contract.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(contract.getBody()).startsWith("openapi: 3.0.3");
        for (String path : List.of("/api/temperature/Paris", "/api/rag")) {
            assertThat(http.postForEntity(path, Map.of("prompt", "hello"), String.class).getStatusCode())
                    .isEqualTo(HttpStatus.NOT_FOUND);
        }
        verifyNoInteractions(model);
    }

    private org.springframework.http.ResponseEntity<String> post(String body) {
        var headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        return http.postForEntity("/api/chat", new HttpEntity<>(body, headers), String.class);
    }

    @SuppressWarnings("unchecked")
    private void assertContractResponse(String status, String body) throws Exception {
        Map<String, Object> contract = new Yaml().load(getClass().getResourceAsStream("/static/openapi.yaml"));
        var paths = (Map<String, Object>) contract.get("paths");
        var chat = (Map<String, Object>) paths.get("/api/chat");
        var operation = (Map<String, Object>) chat.get("post");
        var responses = (Map<String, Object>) operation.get("responses");
        var response = (Map<String, Object>) responses.get(status);
        var content = (Map<String, Object>) response.get("content");
        var media = (Map<String, Object>) content.get("application/json");
        var ref = (Map<String, String>) media.get("schema");
        var components = (Map<String, Object>) contract.get("components");
        var schemas = (Map<String, Object>) components.get("schemas");
        var schema = (Map<String, Object>) schemas.get(ref.get("$ref").replace("#/components/schemas/", ""));
        var properties = (Map<String, Object>) schema.get("properties");
        Map<String, Object> actual = json.readValue(body, Map.class);
        assertThat(actual.keySet()).containsExactlyInAnyOrderElementsOf(properties.keySet());
        for (String required : (List<String>) schema.get("required")) {
            assertThat(actual.get(required)).isInstanceOf(String.class);
            assertThat((String) actual.get(required)).isNotBlank();
        }
    }
}
