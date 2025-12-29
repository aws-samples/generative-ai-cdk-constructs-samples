package org.example.utility;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.Getter;
import lombok.Setter;
import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;
import org.eclipse.jetty.websocket.api.Session;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.services.bedrockruntime.model.ModelStreamErrorException;

import java.io.IOException;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import java.util.Random;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Getter
class ChatTurn {
    private final String role;
    private final String content;

    public ChatTurn(String role, String content) {
        this.role = role;
        this.content = content;
    }
}

public class OutputEventsInteractObserver implements InteractObserver<String> {
    private static final Logger log = LoggerFactory.getLogger(OutputEventsInteractObserver.class);
    private final ObjectMapper objectMapper;
    private final Session session;
    private final List<ChatTurn> localChatHistory;
    private String promptId = "";
    @Setter
    private InteractObserver<String> inputObserver;
    private final AtomicReference<String> toolUseId = new AtomicReference<>("");
    private final AtomicReference<String> toolUseContent = new AtomicReference<>("");
    private final AtomicReference<String> toolName = new AtomicReference<>("");
    private final AtomicReference<String> role = new AtomicReference<>("");
    private final AtomicReference<String> generationStage = new AtomicReference<>("");
    private final AtomicBoolean isCompleted = new AtomicBoolean(false);
    // Executor for asynchronous tool execution (Nova 2 Sonic feature)
    private static final ExecutorService toolExecutor = Executors.newCachedThreadPool();

    public OutputEventsInteractObserver(Session session) {
        this.session = session;
        this.objectMapper = new ObjectMapper();
        this.localChatHistory = new ArrayList<>();
    }

    @Override
    public void onNext(String msg) {
        if (isCompleted.get()) {
            log.warn("Received message after completion, ignoring - session: {}", session.hashCode());
            return;
        }

        try {
            log.debug("Processing message - session: {}, length: {}, isOpen: {}", 
                    session.hashCode(), msg.length(), session.isOpen());
            
            boolean shouldSendMsgToUI = true;
            JsonNode rootNode = objectMapper.readTree(msg);
            JsonNode eventNode = rootNode.get("event");
            
            if (eventNode == null) {
                log.warn("Received message without event node - session: {}", session.hashCode());
                return;
            }

            if (eventNode != null) {
                if (eventNode.has("completionStart")) {
                    handleCompletionStart(eventNode.get("completionStart"));
                } else if (eventNode.has("contentStart")) {
                    if (eventNode.get("contentStart").get("type") == null) {
                        shouldSendMsgToUI = false;
                    }
                    handleContentStart(eventNode.get("contentStart"));
                } else if (eventNode.has("textOutput")) {
                    if (!generationStage.get().equals("SPECULATIVE")) {
                        localChatHistory.add(new ChatTurn(role.get(), eventNode.get("textOutput").get("content").asText()));
                    }
                    handleTextOutput(eventNode.get("textOutput"));
                } else if (eventNode.has("audioOutput")) {
                    handleAudioOutput(eventNode.get("audioOutput"));
                } else if (eventNode.has("toolUse")) {
                    shouldSendMsgToUI = false;
                    toolUseId.set(eventNode.get("toolUse").get("toolUseId").asText());
                    toolUseContent.set(eventNode.get("toolUse").get("content").asText());
                    toolName.set(eventNode.get("toolUse").get("toolName").asText());
                } else if (eventNode.has("contentEnd")) {
                    if ("TOOL".equals(eventNode.get("contentEnd").get("type").asText())) {
                        handleToolUse(eventNode);
                        shouldSendMsgToUI = false;
                    }
                    handleContentEnd(eventNode.get("contentEnd"));
                } else if (eventNode.has("completionEnd")) {
                    handleCompletionEnd(eventNode.get("completionEnd"));
                }
            }

            if (shouldSendMsgToUI) {
                sendToUI(msg);
            }

        } catch (Exception e) {
            log.error("Error processing message - session: {}, error: {}", session.hashCode(), e.getMessage(), e);
            handleError(e);
        }
    }

    private void handleCompletionStart(JsonNode node) {
        log.info("Completion started for node: {}", node);
        promptId = node.get("promptName").asText();
        log.info("Completion started with promptId: {}", promptId);
    }

    private void handleContentStart(JsonNode node) {
        log.info("Content started for node: {}", node);
        try {
            if(node.has("additionalModelFields"))
            {
            String additionalModelFieldsStr = node.get("additionalModelFields").asText();
            ObjectMapper mapper = new ObjectMapper();
            JsonNode additionalFields = mapper.readTree(additionalModelFieldsStr);
            // FINAL is the option for USER
            // SPECULATIVE is the option before audio generation for ASSISTANT
            // FINAL is the other option after audio generation for ASSISTANT
            generationStage.set(additionalFields.get("generationStage").asText());
            }
            if(node.has("role")) {// USER, ASSISTANT, or TOOL
                role.set(node.get("role").asText());
            }
        } catch (Exception e) {
        // Handle other errors
        System.err.println("Error processing content event: " + e.getMessage());
        }
        String contentId = node.get("contentId").asText();
        log.info("Content started with contentId: {}", contentId);
    }

    private void handleTextOutput(JsonNode node) {
        log.info("Text output for node: {}", node);
        String content = node.get("content").asText();
        log.info("Received text output: {} from {}", content, role.get());
    }

    private void handleAudioOutput(JsonNode node) {
        log.info("Audio output for node: {}", node);
        String content = node.get("content").asText();
        log.info("Received audio output {} from {}", content, role.get());
    }

    private void handleToolUse(JsonNode node) {
        if (node == null) {
            log.warn("Received null node in handleToolUse");
            return;
        }

        try {
            validateToolUseParameters();
            // Execute tool asynchronously (Nova 2 Sonic feature: async tool calling)
            // This allows the model to continue responding while tools run in the background
            CompletableFuture.runAsync(() -> {
                try {
                    processToolUse(node);
                } catch (Exception e) {
                    log.error("Error in async tool execution: {}", e.getMessage(), e);
                }
            }, toolExecutor);
            log.info("Tool {} execution started asynchronously (Nova 2 Sonic async tool calling)", toolName.get());
        } catch (IllegalStateException e) {
            log.error("Tool use processing failed: {}", e.getMessage());
        }
    }

    private void validateToolUseParameters() {
        if (toolName.get() == null || toolUseId.get() == null || promptId == null) {
            throw new IllegalStateException("Missing required tool use parameters");
        }
    }

    private void processToolUse(JsonNode node) {
        log.debug("Processing tool use for node: {}", node);
        String localChatHistory = createChatHistoryFromLocal();
        logChatHistories(localChatHistory);
        String contentID = UUID.randomUUID().toString();
        sendStart(contentID);
        sendResult(contentID);
        sendEnd(contentID);
    }

    private void sendResult (String contentId)
    {
        if (inputObserver != null) {
            try {
                // Create the "toolResult" object
                ObjectNode toolResultNode = objectMapper.createObjectNode();
                toolResultNode.put("promptName", promptId);
                toolResultNode.put("contentName", contentId);
                ObjectNode contentNode = objectMapper.createObjectNode();
                switch (toolName.get()) {
                    case "getDateAndTimeTool" : {
                        LocalDate currentDate = LocalDate.now(ZoneId.of("America/Los_Angeles"));
                        ZonedDateTime pstTime = ZonedDateTime.now(ZoneId.of("America/Los_Angeles"));
                        contentNode.put("date", currentDate.format(DateTimeFormatter.ISO_DATE));
                        contentNode.put("year", currentDate.getYear());
                        contentNode.put("month", currentDate.getMonthValue());
                        contentNode.put("day", currentDate.getDayOfMonth());
                        contentNode.put("dayOfWeek", currentDate.getDayOfWeek().toString());
                        contentNode.put("timezone", "PST");
                        contentNode.put("formattedTime", pstTime.format(DateTimeFormatter.ofPattern("HH:mm")));
                        break;

                    }
                    case "getWeatherTool": {
                        log.info("Weather tool called");
                        try {
                            // Parse the tool content to get latitude and longitude
                            JsonNode toolContent = objectMapper.readTree(toolUseContent.get());
                            double latitude = toolContent.get("latitude").asDouble();
                            double longitude = toolContent.get("longitude").asDouble();
                            
                            // Call the weather API
                            Map<String, Object> weatherData = fetchWeatherData(latitude, longitude);
                            
                            // Convert map to JsonNode and add it to content
                            contentNode = objectMapper.valueToTree(weatherData);
                            
                        } catch (Exception e) {
                            log.error("Error processing weather tool request", e);
                            contentNode.put("error", "Failed to fetch weather data: " + e.getMessage());
                        }
                        break;
                    }
                    default: {
                        log.warn("Unhandled tool: {}", toolName.get());
                    }
                }

                toolResultNode.put("content", objectMapper.writeValueAsString(contentNode)); // Ensure proper escaping
                // Create the final JSON structure
                ObjectNode eventNode = objectMapper.createObjectNode();
                eventNode.set("toolResult", toolResultNode);

                ObjectNode rootNode = objectMapper.createObjectNode();
                rootNode.set("event", eventNode);
                inputObserver.onNext(objectMapper.writeValueAsString(rootNode));

            } catch (Exception e) {
                throw new RuntimeException("Error creating JSON payload for toolResult", e);
            }
        }

    }

    private Map<String, Object> fetchWeatherData(double latitude, double longitude) throws IOException {
        String url = "https://api.open-meteo.com/v1/forecast?latitude=" + latitude + 
                     "&longitude=" + longitude + "&current_weather=true";

        try {
            RequestConfig config = RequestConfig.custom()
                .setConnectTimeout(5000)
                .setSocketTimeout(5000)
                .build();

            CloseableHttpClient httpClient = HttpClients.custom()
                .setDefaultRequestConfig(config)
                .build();

            HttpGet request = new HttpGet(url);
            request.addHeader("User-Agent", "MyApp/1.0");
            request.addHeader("Accept", "application/json");

            CloseableHttpResponse response = httpClient.execute(request);
            String responseBody = EntityUtils.toString(response.getEntity());
            
            ObjectMapper mapper = new ObjectMapper();
            Map<String, Object> weatherData = mapper.readValue(responseBody, Map.class);
            
            log.info("weatherData: " + weatherData);
            
            Map<String, Object> result = new HashMap<>();
            result.put("weather_data", weatherData);
            return result;
            
        } catch (IOException error) {
            System.err.println("Error fetching weather data: " + error.getMessage());
            throw error;
        }
    }


    private void sendStart(String contentId) {
        if (inputObserver != null) {
            try {
                ObjectNode rootNode = objectMapper.createObjectNode();
                ObjectNode eventNode = rootNode.putObject("event");
                ObjectNode contentStartNode = eventNode.putObject("contentStart");

                contentStartNode.put("promptName", promptId);
                contentStartNode.put("contentName", contentId);
                contentStartNode.put("interactive", false);
                contentStartNode.put("type", "TOOL");
                contentStartNode.put("role", "TOOL");
                ObjectNode toolResultInputConfigNode = contentStartNode.putObject("toolResultInputConfiguration");
                toolResultInputConfigNode.put("toolUseId", toolUseId.get());
                toolResultInputConfigNode.put("type", "TEXT");

                ObjectNode textInputConfigNode = toolResultInputConfigNode.putObject("textInputConfiguration");
                textInputConfigNode.put("mediaType", "text/plain");

                String contentStart = objectMapper.writeValueAsString(rootNode);
                inputObserver.onNext(contentStart);
            } catch (Exception e) {
                throw new RuntimeException("Error creating JSON payload for Tool Result contentStart", e);
            }
        }
    }

    private void sendEnd(String contentId) {
        if (inputObserver != null) {
            try {
                ObjectNode rootNode = objectMapper.createObjectNode();
                ObjectNode eventNode = rootNode.putObject("event");
                ObjectNode contentEndNode = eventNode.putObject("contentEnd");

                contentEndNode.put("promptName", promptId);
                contentEndNode.put("contentName", contentId);

                String contentEndJson = objectMapper.writeValueAsString(rootNode);
                inputObserver.onNext(contentEndJson);
            } catch (Exception e) {
                throw new RuntimeException("Error creating JSON payload for Tool Result contentEnd", e);
            }
        }
    }

    private void logChatHistories(String localChatHistory) {
        log.debug("Actual chat History: {}", toolUseContent.get());
        log.debug("Local Chat History: {}", localChatHistory);
    }

    private void handleContentEnd(JsonNode node) {
        log.info("Content end for node: {}", node);
        String contentId = node.get("contentId").asText();
        String stopReason = node.has("stopReason") ? node.get("stopReason").asText() : "";
        log.info("Content ended: {} with reason: {}", contentId, stopReason);
    }

    private void handleCompletionEnd(JsonNode node) {
        log.info("Completion end for node: {}", node);
        String stopReason = node.has("stopReason") ? node.get("stopReason").asText() : "";
        log.info("Completion ended with reason: {}", stopReason);
    }

    private void sendToUI(String msg) {
        try {
            if (session.isOpen()) {
                log.debug("Sending message to UI - session: {}, length: {}, lastAccessed: {}ms ago", 
                        session.hashCode(), msg.length(), 
                        System.currentTimeMillis() - session.getIdleTimeout().toMillis());
                session.getRemote().sendString(msg);
            } else {
                log.warn("Cannot send message - session closed - session: {}, idleTimeout: {}ms, lastAccessed: {}ms ago",
                        session.hashCode(), session.getIdleTimeout(),
                        System.currentTimeMillis() - session.getIdleTimeout().toMillis());
            }
        } catch (Exception e) {
            log.error("Error sending message to UI - session: {}, error: {}", 
                    session.hashCode(), e.getMessage(), e);
            handleError(e);
        }
    }

    private String createChatHistoryFromLocal() {
        JSONArray messageJsonArray = new JSONArray();
        for (ChatTurn cc : localChatHistory) {
            JSONObject messageObj = new JSONObject();
            messageObj.put("role", cc.getRole());
            messageObj.put("content", cc.getContent());
            messageJsonArray.put(messageObj);
        }
        JSONObject chatHistoryObj = new JSONObject();
        chatHistoryObj.put("chatHistory", messageJsonArray);
        return chatHistoryObj.toString();
    }

    @Override
    public void onComplete() {
        if (isCompleted.compareAndSet(false, true)) {
            log.info("Output complete - session: {}, isOpen: {}", session.hashCode(), session.isOpen());
            try {
                if (session.isOpen()) {
                    session.close(1000, "Output complete");
                    log.info("Session closed successfully");
                } else {
                    log.warn("Session already closed during completion");
                }
            } catch (Exception e) {
                log.error("Error closing session on completion - session: {}, error: {}", 
                        session.hashCode(), e.getMessage(), e);
            }
        }
    }

    @Override
    public void onError(Exception error) {
        handleError(error);
    }

    private void handleError(Exception error) {
        if (isCompleted.compareAndSet(false, true)) {
            log.error("Error occurred - session: {}, isOpen: {}, error: {}", 
                    session.hashCode(), session != null && session.isOpen(), error.getMessage(), error);

            try {
                if (session != null && session.isOpen()) {
                    String errorMessage = error.getMessage();
                    if (error instanceof ModelStreamErrorException) {
                        ModelStreamErrorException mse = (ModelStreamErrorException) error;
                        errorMessage = String.format("Bedrock service error (Status: %d, RequestId: %s): %s",
                            mse.statusCode(), mse.requestId(), mse.getMessage());
                    }
                    session.close(1011, "Error occurred: " + errorMessage);
                    log.info("Session closed due to error");
                } else {
                    log.warn("Session already closed during error handling");
                }
            } catch (Exception e) {
                log.error("Error closing session after error - session: {}, error: {}", 
                        session != null ? session.hashCode() : "null", e.getMessage(), e);
            }
        }
    }
}
