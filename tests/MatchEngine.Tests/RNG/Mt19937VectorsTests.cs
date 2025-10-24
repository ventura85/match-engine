using MatchEngine.Core.Engine.RNG;
using Xunit;

namespace MatchEngine.Tests.RNG;

public class Mt19937VectorsTests
{
    [Fact]
    public void ReferenceVectors_Seed5489_First10Match()
    {
        // Canonical MT19937 vectors for seed 5489
        uint[] expected =
        {
            3499211612u, 581869302u, 3890346734u, 3586334585u, 545404204u,
            4161255391u, 3922919429u, 949333985u, 2715962298u, 1323567403u
        };

        var mt = new Mt19937();
        mt.Seed(5489);

        for (int i = 0; i < expected.Length; i++)
        {
            uint actual = mt.NextUInt32();
            Assert.Equal(expected[i], actual);
        }
    }
}

