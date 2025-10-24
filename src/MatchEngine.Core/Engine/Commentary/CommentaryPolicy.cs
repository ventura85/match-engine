using System;
using System.Collections.Generic;

namespace MatchEngine.Core.Engine.Commentary;

/// <summary>
/// Per-event commentary rates and minute-based cooldowns.
/// </summary>
public sealed class CommentaryPolicy
{
    // Default probabilities and cooldowns in minutes per event name
    private readonly Dictionary<string, (double rate, int cooldownMin)> _map =
        new(StringComparer.OrdinalIgnoreCase)
        {
            // Always-on key events
            ["Goal"] = (1.0, 0),
            ["ShotOnTarget"] = (1.0, 0),
            ["SaveMade"] = (1.0, 0),
            ["RedCard"] = (1.0, 0),
            ["PenaltyAwarded"] = (1.0, 0),
            ["FreekickAwarded"] = (1.0, 0),
            ["CornerAwarded"] = (1.0, 0),
            ["FinalWhistle"] = (1.0, 0),
            ["Kickoff"] = (1.0, 0),
            ["HalfTime"] = (1.0, 0),

            // Others
            ["Shot"] = (0.80, 1),
            ["FoulCommitted"] = (0.50, 1),
            ["YellowCard"] = (0.50, 1),
            ["BuildUp"] = (0.20, 2),
            ["FinalThird"] = (0.30, 1),
            ["DuelWon"] = (0.25, 1),
            ["DuelLost"] = (0.25, 1),
        };

    public int GlobalCooldownEvents { get; init; } = 2;
    public int MaxPerMinute { get; init; } = 1;

    public (double rate, int cooldownMin) Get(string eventName)
    {
        if (_map.TryGetValue(eventName, out var v)) return v;
        return (0.0, 0);
    }
}
