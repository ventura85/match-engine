using System;
using System.Collections.Generic;
using System.Linq;
using MatchEngine.Core.Domain.Players;
using MatchEngine.Core.Domain.Roles;

namespace MatchEngine.Core.Domain.Teams;

/// <summary>
/// Team definition with formation, tactics, squad and starting XI role map.
/// </summary>
public class Team
{
    /// <summary>
    /// Team display name.
    /// </summary>
    public string Name { get; init; } = string.Empty;

    /// <summary>
    /// Chosen formation.
    /// </summary>
    public Formation Formation { get; init; }

    /// <summary>
    /// Tactical configuration.
    /// </summary>
    public Tactics Tactics { get; init; }

    /// <summary>
    /// Squad list (must contain at least 11 players for a valid team).
    /// </summary>
    public IReadOnlyList<Player> Players { get; init; } = Array.Empty<Player>();

    /// <summary>
    /// Starting XI mapping: Role -> array of player indices in <see cref="Players"/>.
    /// </summary>
    public IReadOnlyDictionary<Role, int[]> RoleMap { get; init; } = new Dictionary<Role, int[]>();

    /// <summary>
    /// Validates the team consistency and starting XI constraints.
    /// </summary>
    public bool Validate(out List<string> errors)
    {
        errors = new List<string>();

        if (Players == null || Players.Count < 11)
        {
            errors.Add("Team must have at least 11 players.");
            return false;
        }

        if (RoleMap == null || RoleMap.Count == 0)
        {
            errors.Add("RoleMap must define starters.");
            return false;
        }

        // Flatten all starter indices and verify existence and uniqueness
        var starters = new List<int>();
        foreach (var kv in RoleMap)
        {
            foreach (var idx in kv.Value)
            {
                if (idx < 0 || idx >= Players.Count)
                {
                    errors.Add($"Role {kv.Key}: index {idx} out of range.");
                }
                else
                {
                    starters.Add(idx);
                }
            }
        }

        // Must be exactly 11 unique starters
        if (starters.Count != 11)
        {
            errors.Add($"RoleMap must reference exactly 11 starters, got {starters.Count}.");
        }

        var distinct = starters.Distinct().ToList();
        if (distinct.Count != starters.Count)
        {
            errors.Add("Duplicate starter index detected across roles.");
        }

        // MVP key constraints: at least 1 GK and 2 CB
        int gkCount = RoleMap.TryGetValue(Role.GK, out var gk) ? gk.Length : 0;
        int cbCount = RoleMap.TryGetValue(Role.CB, out var cb) ? cb.Length : 0;

        if (!Formation.RequiresAtLeast(Role.GK, gkCount))
        {
            errors.Add("Formation requires at least 1 GK.");
        }
        if (!Formation.RequiresAtLeast(Role.CB, cbCount))
        {
            errors.Add("Formation requires at least 2 CBs.");
        }

        return errors.Count == 0;
    }
}

