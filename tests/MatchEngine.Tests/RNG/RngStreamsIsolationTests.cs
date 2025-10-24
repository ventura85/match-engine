using MatchEngine.Core.Engine.RNG;
using Xunit;

namespace MatchEngine.Tests.RNG;

public class RngStreamsIsolationTests
{
    [Fact]
    public void Streams_IsolatedBetweenNames_AndCachedPerRegistry()
    {
        var regA = new RngRegistry(12345);
        var regB = new RngRegistry(12345);

        // Burn 500 values from a different stream in regA
        var commentaryA = regA.Get("commentary");
        for (int i = 0; i < 500; i++)
        {
            _ = commentaryA.NextDouble();
        }

        // Retrieve "shots" stream from both registries
        var shotsA1 = regA.Get("shots");
        var shotsA2 = regA.Get("shots");
        var shotsB = regB.Get("shots");

        // Ensure caching returns the same instance within a registry
        Assert.Same(shotsA1, shotsA2);

        // Collect sequences
        uint[] seqA = new uint[100];
        uint[] seqB = new uint[100];
        for (int i = 0; i < 100; i++)
        {
            seqA[i] = shotsA1.NextUInt32();
            seqB[i] = shotsB.NextUInt32();
        }

        Assert.Equal(seqA, seqB);
    }
}

