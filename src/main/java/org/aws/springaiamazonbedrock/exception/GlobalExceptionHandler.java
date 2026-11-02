package org.aws.springaiamazonbedrock.exception;

import org.aws.springaiamazonbedrock.model.ErrorResponse;
import org.aws.springaiamazonbedrock.service.BedrockUnavailableException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {
    private static final Logger LOG = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler({MethodArgumentNotValidException.class, HttpMessageNotReadableException.class})
    public ResponseEntity<ErrorResponse> invalidRequest(Exception exception) {
        return ResponseEntity.badRequest().body(new ErrorResponse(
                "Request must contain only a prompt with 1 to 4000 nonblank characters."));
    }

    @ExceptionHandler(BedrockUnavailableException.class)
    public ResponseEntity<ErrorResponse> unavailable(BedrockUnavailableException exception) {
        LOG.warn("Bedrock call failed: {}", exception.getCause().getClass().getSimpleName());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(new ErrorResponse(exception.getMessage()));
    }
}
