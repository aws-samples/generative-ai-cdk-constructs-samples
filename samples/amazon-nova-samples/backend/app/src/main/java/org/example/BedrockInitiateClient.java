package org.example;

import org.example.websocket.WebSocketServer;

public class BedrockInitiateClient {
    public static void main(String[] args) {
        // Get port from environment variable
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "80"));
        WebSocketServer server = new WebSocketServer(port);

        // Add shutdown hook
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("Shutting down server...");
            try {
                server.stop();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }));

        try {
            server.start();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
