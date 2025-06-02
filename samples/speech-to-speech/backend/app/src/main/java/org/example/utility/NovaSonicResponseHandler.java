package org.example.utility;

import java.util.Objects;
import java.util.concurrent.atomic.AtomicBoolean;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.core.async.SdkPublisher;
import software.amazon.awssdk.services.bedrockruntime.model.BidirectionalOutputPayloadPart;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidirectionalStreamOutput;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidirectionalStreamResponse;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidirectionalStreamResponseHandler;
import software.amazon.awssdk.services.bedrockruntime.model.ModelStreamErrorException;

import java.nio.charset.StandardCharsets;

public class NovaSonicResponseHandler implements InvokeModelWithBidirectionalStreamResponseHandler {
    private static final Logger log = LoggerFactory.getLogger(NovaSonicResponseHandler.class);
    private final InteractObserver<String> delegate;
    private final AtomicBoolean isCompleted = new AtomicBoolean(false);

    public NovaSonicResponseHandler(InteractObserver<String> delegate) {
        this.delegate = Objects.requireNonNull(delegate, "delegate cannot be null");
    }

    @Override
    public void responseReceived(InvokeModelWithBidirectionalStreamResponse response) {
        log.info("Amazon Nova Sonic request id: {}", response.responseMetadata().requestId());
    }

    @Override
    public void onEventStream(SdkPublisher<InvokeModelWithBidirectionalStreamOutput> sdkPublisher) {
        log.info("Amazon Nova Sonic event stream received");
        var completableFuture = sdkPublisher.subscribe((output) -> output.accept(new Visitor() {
            @Override
            public void visitChunk(BidirectionalOutputPayloadPart event) {
                if (isCompleted.get()) {
                    log.warn("Received chunk after stream completion, ignoring");
                    return;
                }
                try {
                    log.info("Nova Sonic chunk received, converting to payload");
                    String payloadString =
                            StandardCharsets.UTF_8.decode((event.bytes().asByteBuffer().rewind().duplicate())).toString();
                    log.info("Nova Sonic payload: {}", payloadString);
                    delegate.onNext(payloadString);
                } catch (Exception e) {
                    log.error("Error processing chunk: {}", e.getMessage(), e);
                    handleError(e);
                }
            }
        }));

        // Handle stream completion and errors
        completableFuture.whenComplete((result, error) -> {
            if (error != null) {
                handleError(error);
            } else {
                complete();
            }
        });
    }

    @Override
    public void exceptionOccurred(Throwable t) {
        handleError(t);
    }

    @Override
    public void complete() {
        if (isCompleted.compareAndSet(false, true)) {
            log.info("Nova Sonic stream completed successfully");
            delegate.onComplete();
        }
    }

    private void handleError(Throwable t) {
        if (isCompleted.compareAndSet(false, true)) {
            if (t instanceof ModelStreamErrorException) {
                ModelStreamErrorException mse = (ModelStreamErrorException) t;
                log.error("Nova Sonic stream error - Status: {}, RequestId: {}, Message: {}", 
                    mse.statusCode(), mse.requestId(), mse.getMessage());
                delegate.onError(new Exception(mse));
            } else {
                log.error("Nova Sonic stream error: {}", t.getMessage(), t);
                delegate.onError(new Exception(t));
            }
        }
    }
}
