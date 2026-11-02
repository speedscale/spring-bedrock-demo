package org.aws.springaiamazonbedrock.controller;

import jakarta.validation.Valid;
import org.aws.springaiamazonbedrock.model.ChatRequest;
import org.aws.springaiamazonbedrock.model.ChatResponse;
import org.aws.springaiamazonbedrock.service.ChatService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class ChatController {
    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping("/api/chat")
    public ChatResponse chat(@Valid @RequestBody ChatRequest request) {
        return new ChatResponse(chatService.chat(request.prompt()));
    }
}
