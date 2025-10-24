using System;
using System.Collections.Generic;
using MatchEngine.Core.Domain.Players;
using MatchEngine.Core.Domain.Roles;

namespace MatchEngine.Core.Domain.Teams.Presets;

/// <summary>
/// Static set of preset teams for testing.
/// </summary>
public static class SeedData
{
    /// <summary>
    /// Red team in 4-3-3 with attacking style.
    /// </summary>
    public static Team Red_433_Attacking()
    {
        var players = BuildSquad("RED");
        var roleMap = new Dictionary<Role, int[]>
        {
            [Role.GK] = new[] { 0 },
            [Role.FB] = new[] { 1, 4 }, // LB, RB
            [Role.CB] = new[] { 2, 3 },
            [Role.CM] = new[] { 5, 6, 7 },
            [Role.W]  = new[] { 8, 9 },
            [Role.ST] = new[] { 10 },
        };
        var team = new Team
        {
            Name = "Red FC",
            Formation = new Formation("4-3-3"),
            Tactics = new Tactics(Style.Attacking, Tempo.Fast, Width.Wide, LineHeight.High, Pressing.High, Aggression.High, AttackFocus.Wings, new SetPieces("near-post", "long")),
            Players = players,
            RoleMap = roleMap
        };
        return team;
    }

    /// <summary>
    /// Blue team in 4-1-4-1 with balanced style.
    /// </summary>
    public static Team Blue_4141_Balanced()
    {
        var players = BuildSquad("BLUE");
        var roleMap = new Dictionary<Role, int[]>
        {
            [Role.GK] = new[] { 0 },
            [Role.FB] = new[] { 1, 4 },
            [Role.CB] = new[] { 2, 3 },
            [Role.DM] = new[] { 5 },
            [Role.CM] = new[] { 6, 7 },
            [Role.W]  = new[] { 8, 9 },
            [Role.ST] = new[] { 10 },
        };
        var team = new Team
        {
            Name = "Blue United",
            Formation = new Formation("4-1-4-1"),
            Tactics = new Tactics(Style.Balanced, Tempo.Normal, Width.Normal, LineHeight.Mid, Pressing.Med, Aggression.Med, AttackFocus.Mixed, new SetPieces("short", "short")),
            Players = players,
            RoleMap = roleMap
        };
        return team;
    }

    /// <summary>
    /// Grey team in 5-4-1 with defensive style.
    /// </summary>
    public static Team Grey_541_Defensive()
    {
        var players = BuildSquad("GREY");
        var roleMap = new Dictionary<Role, int[]>
        {
            [Role.GK] = new[] { 0 },
            [Role.FB] = new[] { 1, 5 },
            [Role.CB] = new[] { 2, 3, 4 },
            [Role.CM] = new[] { 6, 7 },
            [Role.W]  = new[] { 8, 9 },
            [Role.ST] = new[] { 10 },
        };
        var team = new Team
        {
            Name = "Grey Town",
            Formation = new Formation("5-4-1"),
            Tactics = new Tactics(Style.Defensive, Tempo.Slow, Width.Narrow, LineHeight.Low, Pressing.Low, Aggression.Low, AttackFocus.Center, new SetPieces("far-post", "long")),
            Players = players,
            RoleMap = roleMap
        };
        return team;
    }

    private static List<Player> BuildSquad(string prefix)
    {
        var list = new List<Player>();
        for (int i = 0; i < 16; i++)
        {
            var a = new Attributes();
            // Baseline and gentle variation 55..85
            int baseVal = 60 + (i % 6) * 5; // 60,65,70,75,80,85
            // Physical tweaks
            a.Pace = baseVal;
            a.Accel = baseVal;
            a.Stamina = baseVal - 5 < 0 ? 0 : baseVal - 5;
            a.Strength = baseVal;
            a.Jumping = baseVal - 5 < 0 ? 0 : baseVal - 5;
            a.Agility = baseVal;
            a.Balance = baseVal;
            // Technical tweaks
            a.FirstTouch = baseVal + 5 <= 100 ? baseVal + 5 : 100;
            a.Dribbling = baseVal;
            a.Crossing = baseVal - 5 < 0 ? 0 : baseVal - 5;
            a.ShortPass = baseVal + 5 <= 100 ? baseVal + 5 : 100;
            a.LongPass = baseVal;
            a.Finishing = baseVal;
            a.Heading = baseVal - 5 < 0 ? 0 : baseVal - 5;
            a.Tackling = baseVal;
            a.Marking = baseVal;
            a.Interceptions = baseVal;
            a.SetPieces = baseVal;
            a.Penalties = baseVal;
            a.LongShots = baseVal;
            // Mental tweaks
            a.Vision = baseVal + 5 <= 100 ? baseVal + 5 : 100;
            a.Decision = baseVal;
            a.Anticipation = baseVal;
            a.Composure = baseVal;
            a.OffBall = baseVal;
            a.Positioning = baseVal;
            a.Bravery = baseVal;
            a.Aggression = baseVal;
            a.Leadership = baseVal - 5 < 0 ? 0 : baseVal - 5;
            a.Teamwork = baseVal;
            a.WorkRate = baseVal;

            list.Add(new Player
            {
                Id = i + 1,
                Name = $"{prefix}-Player-{i + 1}",
                Foot = (i % 3) switch { 0 => Footedness.Right, 1 => Footedness.Left, _ => Footedness.Both },
                Traits = Array.Empty<Trait>(),
                Attr = a,
                Form = 1.0,
                Energy = 1.0,
                Morale = 1.0,
            });
        }
        return list;
    }
}

