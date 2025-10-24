namespace MatchEngine.Core.Engine.Events;

/// <summary>
/// Maps event numeric codes to canonical string names used by commentary templates.
/// </summary>
public static class EventCatalog
{
    /// <summary>
    /// Returns the canonical event name for the given code.
    /// </summary>
    public static string GetName(int code) => code switch
    {
        0 => "Kickoff",
        1 => "BuildUp",
        2 => "FinalThird",
        3 => "Shot",
        4 => "ShotOnTarget",
        5 => "Goal",
        6 => "CornerAwarded",
        7 => "FreekickAwarded",
        8 => "PenaltyAwarded",
        9 => "FoulCommitted",
        10 => "YellowCard",
        11 => "RedCard",
        12 => "DuelWon",
        13 => "DuelLost",
        14 => "SaveMade",
        15 => "HalfTime",
        16 => "FinalWhistle",
        _ => "Unknown",
    };
}

