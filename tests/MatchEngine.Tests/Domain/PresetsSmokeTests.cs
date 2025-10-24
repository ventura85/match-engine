using System;
using System.Collections.Generic;
using System.Linq;
using MatchEngine.Core.Domain.Roles;
using MatchEngine.Core.Domain.Teams.Presets;
using Xunit;

namespace MatchEngine.Tests.Domain;

public class PresetsSmokeTests
{
    [Fact]
    public void Red433_Valid()
    {
        var t = SeedData.Red_433_Attacking();
        Assert.True(t.Validate(out var errors), string.Join("; ", errors));
        Assert.True(t.Players.Count >= 11);
        Assert.Equal(11, t.RoleMap.Values.SelectMany(x => x).Distinct().Count());
    }

    [Fact]
    public void Blue4141_Valid()
    {
        var t = SeedData.Blue_4141_Balanced();
        Assert.True(t.Validate(out var errors), string.Join("; ", errors));
        Assert.True(t.Players.Count >= 11);
        Assert.Equal(11, t.RoleMap.Values.SelectMany(x => x).Distinct().Count());
    }

    [Fact]
    public void Grey541_Valid()
    {
        var t = SeedData.Grey_541_Defensive();
        Assert.True(t.Validate(out var errors), string.Join("; ", errors));
        Assert.True(t.Players.Count >= 11);
        Assert.Equal(11, t.RoleMap.Values.SelectMany(x => x).Distinct().Count());
    }
}

