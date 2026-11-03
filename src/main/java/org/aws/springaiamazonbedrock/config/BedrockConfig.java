package org.aws.springaiamazonbedrock.config;

import org.springframework.ai.bedrock.converse.BedrockChatOptions;
import org.springframework.ai.bedrock.converse.BedrockProxyChatModel;
import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
public class BedrockConfig {
    @Bean
    static BeanPostProcessor bedrockRequestOptions() {
        return new BeanPostProcessor() {
            @Override
            public Object postProcessAfterInitialization(Object bean, String beanName) {
                // Sonnet 5.5 rejects the temperature supplied by Spring AI's defaults.
                if (bean instanceof BedrockProxyChatModel model
                        && model.getDefaultOptions() instanceof BedrockChatOptions options) {
                    options.setTemperature(null);
                }
                return bean;
            }
        };
    }
}
