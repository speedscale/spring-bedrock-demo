package org.aws.springaiamazonbedrock.service;

import java.util.List;

import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.stereotype.Service;

@Service
public class ChatService {
    private final ChatModel chatModel;

    public ChatService(ChatModel chatModel) {
        this.chatModel = chatModel;
    }

    public String chat(String prompt) {
        try {
            var result = chatModel.call(new Prompt(List.of(
                    new SystemMessage("You are a helpful support assistant. Give concise answers."),
                    new UserMessage(prompt))));
            if (result == null || result.getResult() == null || result.getResult().getOutput() == null) {
                throw new IllegalStateException("Bedrock returned no message");
            }
            String text = result.getResult().getOutput().getText();
            if (text == null || text.isBlank()) {
                throw new IllegalStateException("Bedrock returned no text");
            }
            return text;
        } catch (RuntimeException exception) {
            throw new BedrockUnavailableException(exception);
        }
    }
}
