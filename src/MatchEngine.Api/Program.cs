using MatchEngine.Core.Domain.Teams.Presets;
using EngineMatch = MatchEngine.Core.Engine.Match.MatchEngine;
using MatchEngine.Api.Dtos;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

var summaries = new[]
{
    "Freezing", "Bracing", "Chilly", "Cool", "Mild", "Warm", "Balmy", "Hot", "Sweltering", "Scorching"
};

app.MapGet("/healthz", () => Results.Ok(new { status = "ok" }));

app.MapGet("/teams", () => new[] { "Red", "Blue", "Grey" });

app.MapPost("/simulate", (SimulateRequest req) =>
{
    var a = req.TeamA.ToLower() switch
    {
        "red" => SeedData.Red_433_Attacking(),
        "blue" => SeedData.Blue_4141_Balanced(),
        "grey" => SeedData.Grey_541_Defensive(),
        _ => SeedData.Red_433_Attacking()
    };
    var b = req.TeamB.ToLower() switch
    {
        "red" => SeedData.Red_433_Attacking(),
        "blue" => SeedData.Blue_4141_Balanced(),
        "grey" => SeedData.Grey_541_Defensive(),
        _ => SeedData.Blue_4141_Balanced()
    };
    var engine = new EngineMatch(a, b, req.Seed);
    var report = engine.Simulate(90);
    return Results.Ok(report);
});

app.MapGet("/weatherforecast", () =>
{
    var forecast =  Enumerable.Range(1, 5).Select(index =>
        new WeatherForecast
        (
            DateOnly.FromDateTime(DateTime.Now.AddDays(index)),
            Random.Shared.Next(-20, 55),
            summaries[Random.Shared.Next(summaries.Length)]
        ))
        .ToArray();
    return forecast;
})
.WithName("GetWeatherForecast");

app.Run();

record WeatherForecast(DateOnly Date, int TemperatureC, string? Summary)
{
    public int TemperatureF => 32 + (int)(TemperatureC / 0.5556);
}
