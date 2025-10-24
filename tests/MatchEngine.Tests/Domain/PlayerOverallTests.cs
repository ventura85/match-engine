using System;
using System.Linq;
using MatchEngine.Core.Domain.Players;
using MatchEngine.Core.Domain.Roles;
using Xunit;

namespace MatchEngine.Tests.Domain;

public class PlayerOverallTests
{
    [Fact]
    public void Overall_ForST_UsesRoleWeightsAndIsAccurate()
    {
        var attr = new Attributes();
        // Baseline 50, with ST-critical boosted to 80
        attr.Finishing = 80;
        attr.FirstTouch = 80;
        attr.OffBall = 80;
        attr.Composure = 80;

        var p = new Player { Id = 1, Name = "Test ST", Foot = Footedness.Right, Attr = attr };

        // Expected using RoleWeights for ST
        var skills = p.Attr.ToSkillMap();
        var weights = RoleWeights.Weights[Role.ST];
        double num = 0, den = 0;
        foreach (var kv in weights)
        {
            den += kv.Value;
            skills.TryGetValue(kv.Key, out var s);
            num += s * kv.Value;
        }
        var expected = den > 0 ? num / den : 0.0;

        var actual = p.Overall(Role.ST);

        Assert.True(Math.Abs(actual - expected) < 1e-6, $"Actual {actual} vs expected {expected}");
    }
}

