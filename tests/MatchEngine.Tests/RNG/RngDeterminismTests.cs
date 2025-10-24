using MatchEngine.Core.Engine.RNG;
using Xunit;

namespace MatchEngine.Tests.RNG;

public class RngDeterminismTests
{
    [Fact]
    public void TwoGenerators_SameSeed_ProduceIdenticalSequence()
    {
        var a = new Mt19937();
        var b = new Mt19937();
        a.Seed(42);
        b.Seed(42);

        for (int i = 0; i < 1000; i++)
        {
            Assert.Equal(a.NextUInt32(), b.NextUInt32());
        }
    }
}

