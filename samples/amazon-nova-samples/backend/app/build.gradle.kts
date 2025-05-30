plugins {
    application
    java
}

repositories {
    mavenCentral()
}

dependencies {
    // AWS SDK v2 dependencies
    implementation(platform("software.amazon.awssdk:bom:2.31.36"))
    implementation("software.amazon.awssdk:bedrockruntime")
    implementation("software.amazon.awssdk:bedrock")
    implementation("software.amazon.awssdk:auth")
    implementation("software.amazon.awssdk:sts")
    implementation("software.amazon.awssdk:sdk-core")
    implementation("software.amazon.awssdk:http-client-spi")
    implementation("software.amazon.awssdk:netty-nio-client")
    implementation("software.amazon.awssdk:aws-core")
    implementation("software.amazon.awssdk:regions")

    // Jetty WebSocket dependencies
    implementation("org.eclipse.jetty:jetty-server:11.0.15")
    implementation("org.eclipse.jetty:jetty-servlet:11.0.15")
    implementation("org.eclipse.jetty.websocket:websocket-jetty-server:11.0.15")
    implementation("org.eclipse.jetty.websocket:websocket-jetty-client:11.0.15")
    implementation("org.eclipse.jetty.websocket:websocket-jetty-api:11.0.15")
    implementation("jakarta.servlet:jakarta.servlet-api:6.0.0")

    // Jackson for JSON handling
    implementation("com.fasterxml.jackson.core:jackson-databind:2.15.2")
    implementation("com.fasterxml.jackson.core:jackson-core:2.15.2")
    implementation("com.fasterxml.jackson.core:jackson-annotations:2.15.2")

    // Lombok
    compileOnly("org.projectlombok:lombok:1.18.30")
    annotationProcessor("org.projectlombok:lombok:1.18.30")

    // Apache HttpClient
    implementation("org.apache.httpcomponents:httpclient:4.5.14")

    // JSON (Updated to latest version to fix GHSA-4jq9-2xhw-jpx7 vulnerability)
    implementation("org.json:json:20250517")

    // RxJava
    implementation("io.reactivex.rxjava3:rxjava:3.1.8")

    // JWT and Auth0
    implementation("com.auth0:java-jwt:4.4.0")
    implementation("software.amazon.awssdk:cognitoidentityprovider")

    // Logging
    implementation("org.slf4j:slf4j-api:2.0.7")
    implementation("ch.qos.logback:logback-classic:1.4.11")

    // Testing
    testImplementation("org.junit.jupiter:junit-jupiter:5.9.2")
    testImplementation("org.mockito:mockito-core:5.3.1")
    testImplementation("org.mockito:mockito-junit-jupiter:5.3.1")
}

application {
    mainClass.set("org.example.BedrockInitiateClient")
}

tasks.test {
    useJUnitPlatform()
}

tasks.jar {
    manifest {
        attributes["Main-Class"] = "org.example.BedrockInitiateClient"
    }
    // Include all runtime dependencies in the JAR
    from(configurations.runtimeClasspath.get().map { if (it.isDirectory) it else zipTree(it) })
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}
