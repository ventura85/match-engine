using System;
using System.Collections.Generic;
using MatchEngine.Core.Domain.Roles;

namespace MatchEngine.Core.Domain.Players;

/// <summary>
/// Player entity with attributes, traits and stateful form/energy/morale.
/// </summary>
public class Player
{
    private double _form = 1.0;
    private double _energy = 1.0;
    private double _morale = 1.0;

    /// <summary>
    /// Numeric identifier.
    /// </summary>
    public int Id { get; init; }

    /// <summary>
    /// Player name.
    /// </summary>
    public string Name { get; init; } = string.Empty;

    /// <summary>
    /// Dominant foot.
    /// </summary>
    public Footedness Foot { get; init; }

    /// <summary>
    /// Player traits.
    /// </summary>
    public IReadOnlyList<Trait> Traits { get; init; } = Array.Empty<Trait>();

    /// <summary>
    /// Core attributes.
    /// </summary>
    public Attributes Attr { get; init; } = new();

    /// <summary>
    /// Recent form [0,1]. Not used in OVR.
    /// </summary>
    public double Form { get => _form; set => _form = Clamp01(value); }

    /// <summary>
    /// Current energy [0,1]. Not used in OVR.
    /// </summary>
    public double Energy { get => _energy; set => _energy = Clamp01(value); }

    /// <summary>
    /// Current morale [0,1]. Not used in OVR.
    /// </summary>
    public double Morale { get => _morale; set => _morale = Clamp01(value); }

    private static double Clamp01(double v) => v < 0 ? 0 : (v > 1 ? 1 : v);

    /// <summary>
    /// Computes the role-specific Overall (OVR) rating using <see cref="RoleWeights"/>.
    /// OVR = Sum(skill[key] * weight) / Sum(weight). Missing skills are treated as 0.
    /// </summary>
    public double Overall(Role role)
    {
        var skills = Attr.ToSkillMap();
        var weights = RoleWeights.Weights[role];

        double num = 0.0;
        double den = 0.0;
        foreach (var kv in weights)
        {
            var key = kv.Key;
            var w = kv.Value;
            den += w;
            if (skills.TryGetValue(key, out var s))
            {
                num += s * w;
            }
            // else skill missing -> contribute 0
        }

        return den > 0 ? num / den : 0.0;
    }
}

