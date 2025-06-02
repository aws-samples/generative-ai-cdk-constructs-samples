package org.example.websocket;

import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.server.ServerConnector;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;
import org.eclipse.jetty.websocket.server.config.JettyWebSocketServletContainerInitializer;
import org.example.utility.NovaSonicBedrockInteractClient;
import org.example.utility.CognitoTokenValidator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.auth.credentials.ContainerCredentialsProvider;
import software.amazon.awssdk.auth.credentials.ProfileCredentialsProvider;
import software.amazon.awssdk.auth.credentials.EnvironmentVariableCredentialsProvider;
import software.amazon.awssdk.auth.credentials.AwsCredentialsProvider;
import software.amazon.awssdk.http.Protocol;
import software.amazon.awssdk.http.ProtocolNegotiation;
import software.amazon.awssdk.http.nio.netty.NettyNioAsyncHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeAsyncClient;

import java.time.Duration;
import java.time.temporal.ChronoUnit;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.FilterConfig;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import java.io.IOException;

public class WebSocketServer {
    private static class CognitoAuthFilter implements Filter {
        private final CognitoTokenValidator tokenValidator;

        public CognitoAuthFilter(CognitoTokenValidator tokenValidator) {
            this.tokenValidator = tokenValidator;
        }

        @Override
        public void init(FilterConfig filterConfig) throws ServletException {
        }

        @Override
        public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) 
                throws IOException, ServletException {
            HttpServletRequest httpRequest = (HttpServletRequest) request;
            HttpServletResponse httpResponse = (HttpServletResponse) response;

            // Extract token from Authorization header
            String authHeader = httpRequest.getHeader("Authorization");
            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                WebSocketServer.log.error("No Authorization header or invalid format");
                httpResponse.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Missing or invalid Authorization header");
                return;
            }

            String token = authHeader.substring(7); // Remove "Bearer " prefix
            if (!tokenValidator.validateToken(token)) {
                WebSocketServer.log.error("Invalid Cognito token");
                httpResponse.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Invalid token");
                return;
            }

            chain.doFilter(request, response);
        }

        @Override
        public void destroy() {
        }
    }

    private static final Logger log = LoggerFactory.getLogger(WebSocketServer.class);

    private final Server server;
    private final int port;
    private final CognitoTokenValidator cognitoTokenValidator;

    public WebSocketServer(int port) {
        this.port = port;
        this.server = new Server();
        
        // Initialize Cognito validator with values from environment
        String userPoolId = System.getenv("COGNITO_USER_POOL_ID");
        String region = System.getenv("AWS_REGION");
        if (userPoolId == null || region == null) {
            throw new IllegalStateException("COGNITO_USER_POOL_ID and AWS_REGION environment variables must be set");
        }
        this.cognitoTokenValidator = new CognitoTokenValidator(userPoolId, region);
    }

    public void start() throws Exception {
        log.info("Starting WebSocket Server on port {}", port);
        
        // Keep the connector configuration simple like in the working example
        ServerConnector connector = new ServerConnector(server);
        connector.setPort(port);
        
        server.addConnector(connector);
        log.debug("Server connector created and configured");

        // Create WebSocket handler
        ServletContextHandler context = new ServletContextHandler(ServletContextHandler.SESSIONS);
        context.setContextPath("/");
        log.debug("ServletContextHandler created with context path '/'");

        // Add health check handler for root path
        HttpServlet healthCheckServlet = new HttpServlet() {
            @Override
            protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
                log.debug("Health check request received from {}", req.getRemoteAddr());
                log.debug("Request method: {}, URI: {}, Protocol: {}", 
                         req.getMethod(), req.getRequestURI(), req.getProtocol());
                
                // Consume any request content to prevent "Unconsumed content" errors
                try {
                    if (req.getContentLength() > 0) {
                        log.debug("Request has content length: {}", req.getContentLength());
                        while (req.getReader().read() != -1) {
                            // Consume the content
                        }
                        log.debug("Request content consumed successfully");
                    } else {
                        log.debug("Request has no content to consume");
                    }
                } catch (IOException e) {
                    log.error("Error consuming request content: {}", e.getMessage(), e);
                }
                
                resp.setStatus(HttpServletResponse.SC_OK);
                resp.getWriter().write("OK");
                log.debug("Health check response sent successfully");
            }
        };
        ServletHolder healthCheckHolder = new ServletHolder(healthCheckServlet);
        context.addServlet(healthCheckHolder, "/");

       

            // Configure WebSocket
        JettyWebSocketServletContainerInitializer.configure(context, (servletContext, wsContainer) -> {
            // Add Cognito authentication filter
            org.eclipse.jetty.servlet.FilterHolder filterHolder = new org.eclipse.jetty.servlet.FilterHolder(new CognitoAuthFilter(cognitoTokenValidator));
            filterHolder.setName("cognitoAuthFilter");
            context.addFilter(filterHolder, "/interact-s2s", java.util.EnumSet.of(jakarta.servlet.DispatcherType.REQUEST));

            // Match the working example's WebSocket settings
            wsContainer.setIdleTimeout(Duration.ofMinutes(5));
            wsContainer.setMaxTextMessageSize(128 * 1024);

            NettyNioAsyncHttpClient.Builder nettyBuilder = NettyNioAsyncHttpClient.builder()
                    .readTimeout(Duration.of(180, ChronoUnit.SECONDS))
                    .maxConcurrency(20)
                    .protocol(Protocol.HTTP2)
                    .protocolNegotiation(ProtocolNegotiation.ALPN);
  
            // Determine if running in production (ECS) environment
            // boolean isProduction = System.getenv("ENVIRONMENT") != null && 
            //                      System.getenv("ENVIRONMENT").equals("AWS");

            // Initialize credentials provider based on deployment type
            AwsCredentialsProvider credentialsProvider;
            try {
                String deploymentType = System.getenv("DEPLOYMENT_TYPE");
                if (deploymentType != null && deploymentType.equals("local")) {
                    log.info("Running locally, using EnvironmentVariableCredentialsProvider");
                    credentialsProvider = EnvironmentVariableCredentialsProvider.create();
                } else {
                    log.info("Running in remote environment, using ContainerCredentialsProvider");
                    credentialsProvider = ContainerCredentialsProvider.builder().build();
                }
                
                // Verify credentials can be retrieved
                credentialsProvider.resolveCredentials();
                log.info("Successfully initialized AWS credentials provider");
            } catch (Exception e) {
                log.error("Failed to initialize AWS credentials: {}", e.getMessage());
                log.error("Stack trace: ", e);
                throw new RuntimeException("Failed to initialize AWS credentials. For local development, ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set.", e);
            }

            BedrockRuntimeAsyncClient client = BedrockRuntimeAsyncClient.builder()
                    .region(Region.US_EAST_1)
                    .credentialsProvider(credentialsProvider)
                    .httpClientBuilder(nettyBuilder)
                    .build();

            NovaSonicBedrockInteractClient interactClient = new NovaSonicBedrockInteractClient(client);
            //wsContainer.addMapping("/interact-s2s", (req, resp) -> new InteractWebSocket(interactClient));
            // In your WebSocketServletContainerInitializer.configure method, add this:
            wsContainer.addMapping("/interact-s2s", (req, resp) -> new InteractWebSocket(interactClient));

        });

        server.setHandler(context);

        server.start();
        log.info("WebSocket Server started on port {}", port);
        
        server.join();
    }

    public void stop() throws Exception {
        server.stop();
    }
}
