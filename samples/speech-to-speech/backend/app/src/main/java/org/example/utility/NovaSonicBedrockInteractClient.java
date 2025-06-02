package org.example.utility;

import io.reactivex.rxjava3.processors.ReplayProcessor;
import io.reactivex.rxjava3.schedulers.Schedulers;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeAsyncClient;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidirectionalStreamInput;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidirectionalStreamRequest;
import software.amazon.awssdk.services.bedrockruntime.model.ValidationException;
import software.amazon.awssdk.services.bedrockruntime.model.ModelStreamErrorException;

import java.nio.channels.ClosedChannelException;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

public class NovaSonicBedrockInteractClient {
    private static final Logger log = LoggerFactory.getLogger(NovaSonicBedrockInteractClient.class);
    private final BedrockRuntimeAsyncClient bedrockClient;
    private static final int MAX_RETRIES = 3;
    private static final long INITIAL_BACKOFF_MS = 1000;
    private static final long MAX_BACKOFF_MS = 10000;
    private static final long STREAM_TIMEOUT_MINUTES = 1;
    private static final long CHANNEL_CLOSE_TIMEOUT_MS = 5000;
    private static final long SSL_CLOSE_TIMEOUT_MS = 2000;
    private static final long HTTP2_PING_TIMEOUT_MS = 30000;
    private static final int MAX_PING_FAILURES = 3;

    public NovaSonicBedrockInteractClient(BedrockRuntimeAsyncClient bedrockClient) {
        this.bedrockClient = bedrockClient;
    }

    public InteractObserver<String> interactMultimodal(
            String initialRequest,
            InteractObserver<String> outputEventsInteractObserver
    ) {
        log.info("Starting multimodal interaction - request length: {}", initialRequest.length());
        log.debug("Initial request content: {}", initialRequest);
        
        // Validate request before proceeding
        if (initialRequest == null || initialRequest.trim().isEmpty()) {
            throw new IllegalArgumentException("Initial request cannot be null or empty");
        }

        return createStream(initialRequest, outputEventsInteractObserver, 0);
    }

    private InteractObserver<String> createStream(
            String initialRequest,
            InteractObserver<String> outputEventsInteractObserver,
            int retryCount
    ) {
        InvokeModelWithBidirectionalStreamRequest request = InvokeModelWithBidirectionalStreamRequest.builder()
                .modelId("amazon.nova-sonic-v1:0")
                .build();

        // Create a new publisher for each attempt
        ReplayProcessor<InvokeModelWithBidirectionalStreamInput> publisher = ReplayProcessor.createWithTime(
                STREAM_TIMEOUT_MINUTES, TimeUnit.MINUTES, Schedulers.io()
        );

        var responseHandler = new NovaSonicResponseHandler(outputEventsInteractObserver);
        AtomicReference<CompletableFuture<Void>> currentFuture = new AtomicReference<>();
        AtomicBoolean isStreamActive = new AtomicBoolean(true);
        AtomicBoolean isSslActive = new AtomicBoolean(true);
        AtomicInteger pingFailureCount = new AtomicInteger(0);

        currentFuture.set(bedrockClient.invokeModelWithBidirectionalStream(request, publisher, responseHandler));
        log.info("Initiated Bedrock bidirectional stream (attempt {}/{})", retryCount + 1, MAX_RETRIES + 1);

        // Handle stream failures with retry logic
        currentFuture.get().exceptionally(throwable -> {
            if (!isStreamActive.get()) {
                log.warn("Stream already closed, skipping retry");
                return null;
            }

            if (shouldRetry(throwable) && retryCount < MAX_RETRIES) {
                long backoffMs = calculateBackoff(retryCount);
                log.warn("Bedrock stream failed (attempt {}/{}), retrying in {} ms - error: {}", 
                    retryCount + 1, MAX_RETRIES + 1, backoffMs, throwable.getMessage());
                
                try {
                    // Clean up the failed stream
                    cleanupStream(publisher, isStreamActive, isSslActive, pingFailureCount);
                    Thread.sleep(backoffMs);
                    
                    // Create a new stream for the retry
                    createStream(initialRequest, outputEventsInteractObserver, retryCount + 1);
                    return null;
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    log.error("Retry interrupted", e);
                    cleanupStream(publisher, isStreamActive, isSslActive, pingFailureCount);
                    return null;
                }
            }
            
            log.error("Bedrock stream failed permanently after {} attempts - error: {}", 
                retryCount + 1, throwable.getMessage(), throwable);
            cleanupStream(publisher, isStreamActive, isSslActive, pingFailureCount);
            return null;
        });

        // Handle stream completion
        currentFuture.get().thenApply(result -> {
            log.info("Bedrock stream completed successfully");
            cleanupStream(publisher, isStreamActive, isSslActive, pingFailureCount);
            return result;
        });

        // Send initial session start message
        try {
            if (!isStreamActive.get() || !isSslActive.get()) {
                log.warn("Stream or SSL not active, skipping session start message");
                return new InputEventsInteractObserver(publisher);
            }

            log.debug("Sending initial request");
            publisher.onNext(
                    InvokeModelWithBidirectionalStreamInput.chunkBuilder()
                            .bytes(SdkBytes.fromUtf8String(initialRequest))
                            .build()
            );
            log.info("Session start message sent successfully");
        } catch (Exception e) {
            log.error("Failed to send session start message - error: {}", e.getMessage(), e);
            cleanupStream(publisher, isStreamActive, isSslActive, pingFailureCount);
        }

        return new InputEventsInteractObserver(publisher);
    }

    private void cleanupStream(
            ReplayProcessor<InvokeModelWithBidirectionalStreamInput> publisher,
            AtomicBoolean isStreamActive,
            AtomicBoolean isSslActive,
            AtomicInteger pingFailureCount
    ) {
        if (isStreamActive.compareAndSet(true, false)) {
            try {
                // First, try to complete the stream gracefully
                publisher.onComplete();
                
                // Give some time for the stream to close gracefully
                Thread.sleep(CHANNEL_CLOSE_TIMEOUT_MS);
                
                // Then handle SSL cleanup
                if (isSslActive.compareAndSet(true, false)) {
                    try {
                        // Give some time for SSL to close gracefully
                        Thread.sleep(SSL_CLOSE_TIMEOUT_MS);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        log.error("SSL cleanup interrupted", e);
                    }
                }

                // Reset ping failure count
                pingFailureCount.set(0);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.error("Stream cleanup interrupted", e);
            } catch (Exception e) {
                log.error("Error during stream cleanup", e);
            }
        }
    }

    private long calculateBackoff(int retryCount) {
        long backoff = INITIAL_BACKOFF_MS * (long) Math.pow(2, retryCount);
        return Math.min(backoff, MAX_BACKOFF_MS);
    }

    private boolean shouldRetry(Throwable throwable) {
        if (throwable instanceof ValidationException) {
            // Don't retry validation errors as they won't succeed
            return false;
        }
        if (throwable instanceof ModelStreamErrorException) {
            ModelStreamErrorException mse = (ModelStreamErrorException) throwable;
            // Don't retry certain status codes
            return mse.statusCode() != 400 && mse.statusCode() != 401 && mse.statusCode() != 403;
        }
        if (throwable instanceof ClosedChannelException) {
            // Always retry closed channel exceptions
            return true;
        }
        // Check for SSL and HTTP/2 related exceptions
        String message = throwable.getMessage();
        if (message != null) {
            if (message.contains("Failed to send PING")) {
                // Handle ping failures
                return true;
            }
            if (message.contains("SSLEngine closed") || message.contains("HTTP/2 connection closed")) {
                // Handle connection closure
                return true;
            }
        }
        // Retry other exceptions
        return true;
    }
}
