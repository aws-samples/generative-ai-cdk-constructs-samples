package org.example.websocket;

import org.eclipse.jetty.websocket.api.Session;
import org.eclipse.jetty.websocket.api.WebSocketListener;
import org.example.utility.InteractObserver;
import org.example.utility.NovaSonicBedrockInteractClient;
import org.example.utility.OutputEventsInteractObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

public class InteractWebSocket implements WebSocketListener {
    private static final Logger log = LoggerFactory.getLogger(InteractWebSocket.class);

    private final NovaSonicBedrockInteractClient interactClient;
    private final AtomicBoolean expectedInitialRequest = new AtomicBoolean(true);
    private final AtomicReference<Session> sessionRef = new AtomicReference<>();
    private final AtomicReference<InteractObserver<String>> inputObserverRef = new AtomicReference<>();
    private final AtomicBoolean isClosed = new AtomicBoolean(false);

    public InteractWebSocket(NovaSonicBedrockInteractClient interactClient) {
        this.interactClient = interactClient;
    }

    @Override
    public void onWebSocketConnect(Session session) {
        log.info("Web socket connected session={}", session);
        sessionRef.set(session);
    }

    @Override
    public void onWebSocketText(String jsonText) {
        if (isClosed.get()) {
            log.warn("Received message on closed WebSocket, ignoring");
            return;
        }

        try {
            // Parse the message to check if it's an authorization message
            if (jsonText.contains("\"type\":\"authorization\"")) {
                log.info("Received authorization message");
                // Skip processing auth message as it's already handled by the filter
                return;
            }

            // Handle regular messages
            if (expectedInitialRequest.compareAndSet(true, false)) {
                handleInitialRequest(jsonText);
            } else {
                handleRemainingRequests(jsonText);
            }
        } catch (Exception e) {
            log.error("Error processing WebSocket message", e);
            closeWithError("Error processing message: " + e.getMessage());
        }
    }

    private void handleRemainingRequests(String jsonMsg) {
        try {
            log.info("Parsing msg jsonText={}", jsonMsg);
            InteractObserver<String> observer = inputObserverRef.get();
            if (observer != null) {
                observer.onNext(jsonMsg);
            } else {
                log.error("No input observer available for remaining requests");
                closeWithError("Internal server error: No input observer available");
            }
        } catch (Exception e) {
            log.error("Error handling remaining requests", e);
            closeWithError("Error processing request: " + e.getMessage());
        }
    }

    private void handleInitialRequest(String jsonInitialRequestText) {
        try {
            log.info("Parsing initial request jsonText={}", jsonInitialRequestText);
            Session session = sessionRef.get();
            if (session == null || !session.isOpen()) {
                log.error("Session not available or closed for initial request");
                return;
            }

            // Verify this is a session start event
            if (!jsonInitialRequestText.contains("\"sessionStart\"")) {
                log.error("First message must be a session start event");
                closeWithError("First message must be a session start event");
                return;
            }

            OutputEventsInteractObserver outputObserver = new OutputEventsInteractObserver(session);
            InteractObserver<String> inputObserver = interactClient.interactMultimodal(jsonInitialRequestText, outputObserver);
            inputObserverRef.set(inputObserver);
            outputObserver.setInputObserver(inputObserver);
        } catch (Exception e) {
            log.error("Error handling initial request", e);
            closeWithError("Error initializing connection: " + e.getMessage());
        }
    }

    @Override
    public void onWebSocketBinary(byte[] payload, int offset, int len) {
        throw new UnsupportedOperationException("Binary websocket not yet implemented");
    }

    @Override
    public void onWebSocketError(Throwable t) {
        log.error("WebSocket error", t);
        closeWithError("WebSocket error: " + t.getMessage());
    }

    @Override
    public void onWebSocketClose(int statusCode, String reason) {
        log.info("onWebSocketClose: code={} reason={}", statusCode, reason);
        cleanup();
    }

    private void closeWithError(String errorMessage) {
        if (isClosed.compareAndSet(false, true)) {
            Session session = sessionRef.get();
            if (session != null && session.isOpen()) {
                try {
                    session.close(1011, errorMessage);
                } catch (Exception e) {
                    log.error("Error closing WebSocket session", e);
                }
            }
            cleanup();
        }
    }

    private void cleanup() {
        InteractObserver<String> observer = inputObserverRef.getAndSet(null);
        if (observer != null) {
            try {
                observer.onComplete();
            } catch (Exception e) {
                log.error("Error during observer cleanup", e);
            }
        }
        sessionRef.set(null);
    }
}
