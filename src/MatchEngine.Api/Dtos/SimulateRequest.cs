namespace MatchEngine.Api.Dtos;

public sealed class SimulateRequest
{
    public int Seed { get; set; } = 42;
    public string TeamA { get; set; } = "Red";
    public string TeamB { get; set; } = "Blue";
}

