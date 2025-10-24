using System;

namespace MatchEngine.Core.Engine.RNG;

/// <summary>
/// A named random number generator stream that wraps an underlying <see cref="IRng"/>.
/// </summary>
public sealed class RngStream
{
    private readonly IRng _rng;

    /// <summary>
    /// Optional stream name for diagnostics.
    /// </summary>
    public string Name { get; }

    /// <summary>
    /// Creates a new stream wrapper over the provided RNG.
    /// </summary>
    /// <param name="name">Stream name.</param>
    /// <param name="rng">Underlying RNG instance (e.g. <see cref="Mt19937"/>).</param>
    public RngStream(string name, IRng rng)
    {
        Name = name ?? string.Empty;
        _rng = rng ?? throw new ArgumentNullException(nameof(rng));
    }

    /// <inheritdoc cref="IRng.NextUInt32"/>
    public uint NextUInt32() => _rng.NextUInt32();

    /// <inheritdoc cref="IRng.Next(int, int)"/>
    public int Next(int minInclusive, int maxExclusive) => _rng.Next(minInclusive, maxExclusive);

    /// <inheritdoc cref="IRng.NextDouble"/>
    public double NextDouble() => _rng.NextDouble();
}

