using System.Collections.Generic;

namespace MatchEngine.Core.Domain.Roles;

/// <summary>
/// Static weights per role for computing Overall rating from Attributes.
/// Keys in the inner dictionary must match <see cref="Players.Attributes"/> skill names.
/// </summary>
public static class RoleWeights
{
    /// <summary>
    /// Role -> (skill name -> weight). Weights are normalized during OVR computation.
    /// </summary>
    public static IReadOnlyDictionary<Role, IReadOnlyDictionary<string, double>> Weights { get; } =
        new Dictionary<Role, IReadOnlyDictionary<string, double>>
        {
            [Role.GK] = new Dictionary<string, double>
            {
                // No goalkeeper-specific skills in MVP, approximate with available ones
                ["Positioning"] = 0.20,
                ["Composure"] = 0.15,
                ["Decision"] = 0.12,
                ["Anticipation"] = 0.12,
                ["Jumping"] = 0.10,
                ["Strength"] = 0.08,
                ["Vision"] = 0.05,
                ["Leadership"] = 0.06,
                ["Teamwork"] = 0.06,
                ["FirstTouch"] = 0.06
            },
            [Role.CB] = new Dictionary<string, double>
            {
                ["Tackling"] = 0.18,
                ["Marking"] = 0.18,
                ["Interceptions"] = 0.12,
                ["Positioning"] = 0.12,
                ["Strength"] = 0.10,
                ["Heading"] = 0.12,
                ["Aggression"] = 0.06,
                ["Bravery"] = 0.06,
                ["Pace"] = 0.06
            },
            [Role.FB] = new Dictionary<string, double>
            {
                ["Pace"] = 0.14,
                ["Accel"] = 0.12,
                ["Stamina"] = 0.10,
                ["Tackling"] = 0.12,
                ["Marking"] = 0.08,
                ["Crossing"] = 0.12,
                ["ShortPass"] = 0.10,
                ["Dribbling"] = 0.10,
                ["Positioning"] = 0.12
            },
            [Role.DM] = new Dictionary<string, double>
            {
                ["Tackling"] = 0.16,
                ["Interceptions"] = 0.16,
                ["Positioning"] = 0.14,
                ["ShortPass"] = 0.12,
                ["LongPass"] = 0.12,
                ["Decision"] = 0.10,
                ["Aggression"] = 0.10,
                ["Strength"] = 0.10
            },
            [Role.CM] = new Dictionary<string, double>
            {
                ["ShortPass"] = 0.18,
                ["LongPass"] = 0.14,
                ["FirstTouch"] = 0.12,
                ["Vision"] = 0.14,
                ["Decision"] = 0.12,
                ["WorkRate"] = 0.10,
                ["Stamina"] = 0.10,
                ["Dribbling"] = 0.10
            },
            [Role.AM] = new Dictionary<string, double>
            {
                ["FirstTouch"] = 0.16,
                ["Vision"] = 0.16,
                ["Composure"] = 0.12,
                ["Dribbling"] = 0.14,
                ["ShortPass"] = 0.14,
                ["LongShots"] = 0.10,
                ["OffBall"] = 0.10,
                ["Decision"] = 0.08
            },
            [Role.W] = new Dictionary<string, double>
            {
                ["Pace"] = 0.18,
                ["Accel"] = 0.14,
                ["Dribbling"] = 0.16,
                ["Crossing"] = 0.14,
                ["FirstTouch"] = 0.10,
                ["OffBall"] = 0.10,
                ["Composure"] = 0.08,
                ["Stamina"] = 0.10
            },
            [Role.ST] = new Dictionary<string, double>
            {
                ["Finishing"] = 0.30,
                ["FirstTouch"] = 0.14,
                ["OffBall"] = 0.16,
                ["Composure"] = 0.14,
                ["Heading"] = 0.10,
                ["Pace"] = 0.08,
                ["Accel"] = 0.04,
                ["Strength"] = 0.04
            }
        };
}

