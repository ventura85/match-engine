using System.Collections.Generic;
using System.Text;
using System.Text.Json;
using MatchEngine.Core.Engine.Events;

namespace MatchEngine.Core.Reporting;

public static class NdjsonWriter
{
    public static string Write(IEnumerable<Event> stream)
    {
        var sb = new StringBuilder();
        var opts = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
        foreach (var e in stream)
        {
            sb.AppendLine(JsonSerializer.Serialize(new { minute = e.Minute, type = e.Type.ToString(), team = e.Team }, opts));
        }
        return sb.ToString();
    }
}

