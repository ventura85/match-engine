using System.Collections.Generic;

namespace MatchEngine.Core.Domain.Teams.Presets;

/// <summary>
/// Lightweight team preset loaded from JSON. Used for listing and mapping to domain Team.
/// </summary>
public sealed class TeamPreset
{
    public string Id { get; init; } = string.Empty;
    public string Name { get; init; } = string.Empty;
    public string Formation { get; init; } = string.Empty; // e.g., "4-3-3"
    public string Style { get; init; } = string.Empty;     // e.g., "attacking|balanced|defensive"
    public string? AttackBias { get; init; }               // e.g., "wings|center|mixed"
    public List<TeamPlayerPreset> Players { get; init; } = new();
}

/// <summary>
/// Minimal player description for presets. Values typically in [0..100] or [0..1] for normalized.
/// </summary>
public sealed class TeamPlayerPreset
{
    public string Id { get; init; } = string.Empty;
    public string Name { get; init; } = string.Empty;
    public string Role { get; init; } = string.Empty; // GK, CB, FB, DM, CM, AM, W, ST

    // Coarse ratings
    public int Overall { get; init; } = 60;       // 0..100
    public double Stamina { get; init; } = 0.6;   // 0..1 (normalized)
    public double WorkRate { get; init; } = 0.6;  // 0..1 (normalized)
    public double Composure { get; init; } = 0.6; // 0..1 (normalized)
}

