package org.aws.springaiamazonbedrock.service;

public class BedrockUnavailableException extends RuntimeException {
    public BedrockUnavailableException(Throwable cause) {
        super("Bedrock is unavailable. Retry later.", cause);
    }
}
