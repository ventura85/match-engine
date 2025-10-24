using MatchEngine.Core.Domain.Teams;
using MatchEngine.Core.Engine.RNG;

namespace MatchEngine.Core.Engine.Match;

public sealed class MatchState
{
    public readonly Team A;
    public readonly Team B;
    public int Minute { get; set; }
    public int PossA { get; set; }
    public int PossB { get; set; }
    public readonly RngRegistry Rng;

    public MatchState(Team a, Team b, RngRegistry rng)
    {
        A = a;
        B = b;
        Rng = rng;
    }
}

