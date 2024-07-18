using System.Text.Json.Serialization;
using ChatbotDemo.Repositories.Models;

namespace ChatbotDemo.Api.Models;

public record Connection
{
    [JsonPropertyName("connectionId")] public string? ConnectionId { get; init; }

    public ConnectionDto AsDto() => new(ConnectionId);
}