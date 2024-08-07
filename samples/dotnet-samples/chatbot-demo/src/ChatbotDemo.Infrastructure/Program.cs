﻿using Amazon.CDK;
using ChatbotDemo.Infrastructure.Models;
using ChatbotDemo.Infrastructure.Stacks;

namespace ChatbotDemo.Infrastructure
{
    public sealed class Program
    {
        public static void Main(string[] args)
        {
            var app = new App();

            var websocketStack = new WebSocketStack(app, "WebSocketStack");
            var bedrockGuardrailStack = new BedrockGuardrailStack(app, "BedrockGuardrailStack");
            _ = new BedrockAgentStack(app, "BedrockAgentStack", new MultiStackProps
            {
                ConnectionTable = websocketStack.ConnectionTable,
                WebSocketCallbackUrl = websocketStack.WebSocketCallbackUrl,
                GuardrailId = bedrockGuardrailStack.GuardrailId,
                GuardrailVersion = bedrockGuardrailStack.GuardrailVersion
            });


            app.Synth();
        }
    }
}