using System;
using System.Collections.Generic;
using System.Linq;
using MatchEngine.Core.Domain.Players;
using MatchEngine.Core.Domain.Roles;
using MatchEngine.Core.Domain.Teams;
using Xunit;

namespace MatchEngine.Tests.Domain;

public class FormationValidationTests
{
    private static List<Player> MakePlayers(int count)
    {
        var list = new List<Player>();
        for (int i = 0; i < count; i++)
        {
            list.Add(new Player
            {
                Id = i + 1,
                Name = $"P{i + 1}",
                Foot = Footedness.Right,
                Attr = new Attributes()
            });
        }
        return list;
    }

    [Fact]
    public void MissingGK_InRoleMap_FailsValidation()
    {
        var players = MakePlayers(11);
        var team = new Team
        {
            Name = "NoGK",
            Formation = new Formation("4-4-2"),
            Tactics = new Tactics(Style.Balanced, Tempo.Normal, Width.Normal, LineHeight.Mid, Pressing.Med, Aggression.Med, AttackFocus.Mixed, new SetPieces("short","short")),
            Players = players,
            RoleMap = new Dictionary<Role, int[]>
            {
                [Role.CB] = new[] { 1, 2 },
                [Role.FB] = new[] { 3, 4 },
                [Role.CM] = new[] { 5, 6, 7, 8 },
                [Role.ST] = new[] { 9, 10 },
            }
        };
        var ok = team.Validate(out var errors);
        Assert.False(ok);
        Assert.Contains(errors, e => e.Contains("GK", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void DuplicateStarterIndex_FailsValidation()
    {
        var players = MakePlayers(11);
        var team = new Team
        {
            Name = "DupIndex",
            Formation = new Formation("4-4-2"),
            Tactics = new Tactics(Style.Balanced, Tempo.Normal, Width.Normal, LineHeight.Mid, Pressing.Med, Aggression.Med, AttackFocus.Mixed, new SetPieces("short","short")),
            Players = players,
            RoleMap = new Dictionary<Role, int[]>
            {
                [Role.GK] = new[] { 0 },
                [Role.CB] = new[] { 1, 1 }, // duplicate index intentionally
                [Role.FB] = new[] { 2, 3 },
                [Role.CM] = new[] { 4, 5, 6, 7 },
                [Role.ST] = new[] { 8, 9 },
            }
        };
        var ok = team.Validate(out var errors);
        Assert.False(ok);
        Assert.Contains(errors, e => e.Contains("Duplicate", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void ValidMinimalTeam_PassesValidation()
    {
        var players = MakePlayers(13);
        var team = new Team
        {
            Name = "Valid",
            Formation = new Formation("4-3-3"),
            Tactics = new Tactics(Style.Balanced, Tempo.Normal, Width.Normal, LineHeight.Mid, Pressing.Med, Aggression.Med, AttackFocus.Mixed, new SetPieces("short","short")),
            Players = players,
            RoleMap = new Dictionary<Role, int[]>
            {
                [Role.GK] = new[] { 0 },
                [Role.CB] = new[] { 1, 2 },
                [Role.FB] = new[] { 3, 4 },
                [Role.CM] = new[] { 5, 6, 7 },
                [Role.W]  = new[] { 8, 9 },
                [Role.ST] = new[] { 10 },
            }
        };
        var ok = team.Validate(out var errors);
        Assert.True(ok, string.Join("; ", errors));
    }
}

