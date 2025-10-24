using MatchEngine.Core.Domain.Teams.Presets;
using EngineMatch = MatchEngine.Core.Engine.Match.MatchEngine;
using MatchEngine.Api.Dtos;
using Microsoft.Extensions.Configuration;

var builder = WebApplication.CreateBuilder(args);

// CORS for frontend
builder.Services.AddCors(o => o.AddPolicy("frontend", p =>
    p.WithOrigins("http://localhost:5173")
     .AllowAnyHeader()
     .AllowAnyMethod()
));

// Add services to the container.
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

// Repository registration based on configuration
var teamsSource = builder.Configuration["Data:Teams:Source"] ?? "json";
var teamsPath = builder.Configuration["Data:Teams:Path"] ?? "assets/teams";

if (string.Equals(teamsSource, "json", StringComparison.OrdinalIgnoreCase))
{
    // Resolve relative path from content root when possible
    string ResolvePath(string path)
    {
        if (Path.IsPathRooted(path)) return path;
        var contentRoot = builder.Environment.ContentRootPath;
        var p1 = Path.GetFullPath(Path.Combine(contentRoot, path));
        if (Directory.Exists(p1)) return p1;
        // Try parent (solution root) if running from src/MatchEngine.Api
        var p2 = Path.GetFullPath(Path.Combine(contentRoot, "..", "..", path));
        return p2;
    }

    var resolved = ResolvePath(teamsPath);
    builder.Services.AddSingleton<ITeamRepository>(_ => new JsonTeamRepository(resolved));
}
else
{
    // Default to empty JSON repo if unknown source
    builder.Services.AddSingleton<ITeamRepository>(_ => new JsonTeamRepository(teamsPath));
}

var app = builder.Build();

// Enable CORS
app.UseCors("frontend");

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

var summaries = new[]
{
    "Freezing", "Bracing", "Chilly", "Cool", "Mild", "Warm", "Balmy", "Hot", "Sweltering", "Scorching"
};

app.MapGet("/healthz", () => Results.Ok("ok"));

app.MapGet("/teams", (ITeamRepository repo) =>
{
    var items = repo.GetPresets()
        .Select(t => new { id = t.Id, name = t.Name, formation = t.Formation, style = t.Style })
        .ToArray();
    return Results.Ok(items);
});

app.MapPost("/simulate", (ITeamRepository repo, SimulateRequest req) =>
{
    var teamA = repo.LoadTeam(req.TeamA);
    var teamB = repo.LoadTeam(req.TeamB);
    if (teamA is null || teamB is null)
    {
        return Results.BadRequest(new { error = "Unknown team id(s). Use /teams to list available presets." });
    }

    var engine = new EngineMatch(teamA, teamB, req.Seed);
    var report = engine.Simulate(90);
    return Results.Ok(report);
});

app.Run();
