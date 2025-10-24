using System;
using System.Collections.Generic;
using System.Text;

namespace MatchEngine.Core.Engine.RNG;

/// <summary>
/// Registry of named RNG streams derived deterministically from a master seed.
/// Each stream is isolated: consuming values from one stream does not affect others.
/// </summary>
public sealed class RngRegistry
{
    private readonly int _masterSeed;
    private readonly Dictionary<string, RngStream> _streams = new(StringComparer.Ordinal);

    /// <summary>
    /// Creates a new registry with the provided master seed.
    /// </summary>
    /// <param name="masterSeed">Master seed used to derive per-stream seeds.</param>
    public RngRegistry(int masterSeed)
    {
        _masterSeed = masterSeed;
    }

    /// <summary>
    /// Returns a named RNG stream. On first request, the stream is created using a
    /// derived seed based on the master seed and the stream name. Subsequent requests
    /// return the same cached stream instance.
    /// </summary>
    /// <param name="name">Stream name.</param>
    /// <returns>Deterministic <see cref="RngStream"/> associated with <paramref name="name"/>.</returns>
    public RngStream Get(string name)
    {
        if (name is null) throw new ArgumentNullException(nameof(name));

        if (_streams.TryGetValue(name, out var existing))
        {
            return existing;
        }

        // Derive a non-zero seed using FNV-1a over UTF-8 bytes of name.
        uint fnv = 2166136261u; // FNV offset basis
        var bytes = Encoding.UTF8.GetBytes(name);
        for (int i = 0; i < bytes.Length; i++)
        {
            fnv ^= bytes[i];
            fnv *= 16777619u; // FNV prime
        }

        int derived = unchecked((int)(fnv ^ (uint)_masterSeed ^ 0x9E3779B9u));
        if (derived == 0)
        {
            derived = unchecked((int)0x6D2B79F5u);
        }

        var mt = new Mt19937();
        mt.Seed(derived);
        var stream = new RngStream(name, mt);
        _streams[name] = stream;
        return stream;
    }
}

