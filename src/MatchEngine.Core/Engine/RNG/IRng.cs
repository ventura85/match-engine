using System;

namespace MatchEngine.Core.Engine.RNG;

/// <summary>
/// Abstraction for a deterministic random number generator.
/// </summary>
public interface IRng
{
    /// <summary>
    /// Seeds the generator with the provided 32-bit seed value.
    /// </summary>
    /// <param name="seed">Seed value used to initialize the RNG state.</param>
    void Seed(int seed);

    /// <summary>
    /// Returns the next raw 32-bit unsigned integer from the generator.
    /// </summary>
    /// <returns>Next random <see cref="uint"/> from the generator.</returns>
    uint NextUInt32();

    /// <summary>
    /// Returns a random integer in the range [<paramref name="minInclusive"/>, <paramref name="maxExclusive"/>).
    /// </summary>
    /// <param name="minInclusive">Inclusive lower bound.</param>
    /// <param name="maxExclusive">Exclusive upper bound. Must be greater than <paramref name="minInclusive"/>.</param>
    /// <returns>A uniformly distributed integer in the requested range.</returns>
    /// <exception cref="ArgumentOutOfRangeException">Thrown when <paramref name="minInclusive"/> is not less than <paramref name="maxExclusive"/>.</exception>
    int Next(int minInclusive, int maxExclusive);

    /// <summary>
    /// Returns a random double in the interval [0, 1).
    /// </summary>
    /// <returns>Double in [0,1).</returns>
    double NextDouble();
}

