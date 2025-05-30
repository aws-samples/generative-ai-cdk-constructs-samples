package org.example.utility;

import com.auth0.jwt.JWT;
import com.auth0.jwt.JWTVerifier;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.exceptions.JWTVerificationException;
import com.auth0.jwt.interfaces.DecodedJWT;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.cognitoidentityprovider.CognitoIdentityProviderClient;
import software.amazon.awssdk.services.cognitoidentityprovider.model.GetUserPoolMfaConfigRequest;
import software.amazon.awssdk.services.cognitoidentityprovider.model.GetUserPoolMfaConfigResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URL;
import java.net.HttpURLConnection;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import com.fasterxml.jackson.databind.ObjectMapper;

public class CognitoTokenValidator {
    private static final Logger log = LoggerFactory.getLogger(CognitoTokenValidator.class);
    private final String userPoolId;
    private final String region;
    private final String jwksUrl;
    private Map<String, Map<String, String>> jwks;
    private final ObjectMapper objectMapper;

    public CognitoTokenValidator(String userPoolId, String region) {
        this.userPoolId = userPoolId;
        this.region = region;
        this.jwksUrl = String.format("https://cognito-idp.%s.amazonaws.com/%s/.well-known/jwks.json", region, userPoolId);
        this.objectMapper = new ObjectMapper();
        loadJwks();
    }

    private void loadJwks() {
        try {
            URL url = new URL(jwksUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");

            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder response = new StringBuilder();
            String line;

            while ((line = reader.readLine()) != null) {
                response.append(line);
            }
            reader.close();

            Map<String, Object> jwksJson = objectMapper.readValue(response.toString(), Map.class);
            List<Map<String, String>> keysList = (List<Map<String, String>>) jwksJson.get("keys");
            
            // Convert the list of keys to a map keyed by "kid"
            this.jwks = keysList.stream()
                .collect(java.util.stream.Collectors.toMap(
                    key -> key.get("kid"),
                    key -> key
                ));
        } catch (Exception e) {
            log.error("Error loading JWKS", e);
            throw new RuntimeException("Failed to load JWKS", e);
        }
    }

    public boolean validateToken(String token) {
        try {
            DecodedJWT jwt = JWT.decode(token);
            String kid = jwt.getKeyId();
            
            if (kid == null || !jwks.containsKey(kid)) {
                log.error("Invalid key ID (kid) in token");
                return false;
            }

            Map<String, String> jwk = jwks.get(kid);
            String n = jwk.get("n");
            String e = jwk.get("e");

            // Verify token signature and claims
            Algorithm algorithm = Algorithm.RSA256(new RSAPublicKeyProvider(n, e));
            JWTVerifier verifier = JWT.require(algorithm)
                    .withIssuer(String.format("https://cognito-idp.%s.amazonaws.com/%s", region, userPoolId))
                    .build();

            verifier.verify(token);
            return true;
        } catch (JWTVerificationException e) {
            log.error("Token validation failed", e);
            return false;
        }
    }

    // Helper class for RSA public key creation
    private static class RSAPublicKeyProvider implements com.auth0.jwt.interfaces.RSAKeyProvider {
        private final String modulus;
        private final String exponent;

        public RSAPublicKeyProvider(String modulus, String exponent) {
            this.modulus = modulus;
            this.exponent = exponent;
        }

        @Override
        public java.security.interfaces.RSAPublicKey getPublicKeyById(String keyId) {
            return getPublicKey();
        }

        @Override
        public java.security.interfaces.RSAPrivateKey getPrivateKey() {
            return null;
        }

        @Override
        public String getPrivateKeyId() {
            return null;
        }

        private java.security.interfaces.RSAPublicKey getPublicKey() {
            try {
                byte[] modulusBytes = Base64.getUrlDecoder().decode(modulus);
                byte[] exponentBytes = Base64.getUrlDecoder().decode(exponent);

                java.math.BigInteger modulusBigInt = new java.math.BigInteger(1, modulusBytes);
                java.math.BigInteger exponentBigInt = new java.math.BigInteger(1, exponentBytes);

                java.security.spec.RSAPublicKeySpec spec = new java.security.spec.RSAPublicKeySpec(modulusBigInt, exponentBigInt);
                java.security.KeyFactory factory = java.security.KeyFactory.getInstance("RSA");
                return (java.security.interfaces.RSAPublicKey) factory.generatePublic(spec);
            } catch (Exception e) {
                throw new RuntimeException("Error creating RSA public key", e);
            }
        }
    }
}
