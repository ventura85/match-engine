using System;

namespace MatchEngine.Core.Engine.RNG;

/// <summary>
/// MT19937 Mersenne Twister PRNG implementation (32-bit, period 2^19937-1).
/// Conforms to the reference algorithm by Matsumoto and Nishimura.
/// </summary>
public sealed class Mt19937 : IRng
{
    private const int N = 624;
    private const int M = 397;
    private const uint MATRIX_A = 0x9908B0DFu;   // constant vector a
    private const uint UPPER_MASK = 0x80000000u; // most significant w-r bits
    private const uint LOWER_MASK = 0x7FFFFFFFu; // least significant r bits

    private readonly uint[] _mt = new uint[N]; // the array for the state vector
    private int _mti = N + 1;                  // mti==N+1 means mt[N] is not initialized

    /// <summary>
    /// Creates a new generator with an uninitialized state. Call <see cref="Seed"/> before use.
    /// </summary>
    public Mt19937()
    {
    }

    /// <inheritdoc />
    public void Seed(int seed)
    {
        _mt[0] = unchecked((uint)seed);
        for (_mti = 1; _mti < N; _mti++)
        {
            // mt[i] = 1812433253 * (mt[i-1] ^ (mt[i-1] >> 30)) + i
            _mt[_mti] = unchecked(1812433253u * (_mt[_mti - 1] ^ (_mt[_mti - 1] >> 30)) + (uint)_mti);
        }
    }

    /// <inheritdoc />
    public uint NextUInt32()
    {
        uint y;
        uint[] mt = _mt;

        if (_mti >= N)
        {
            // generate N words at one time
            int kk;
            uint mag01_0 = 0u, mag01_1 = MATRIX_A;

            for (kk = 0; kk < N - M; kk++)
            {
                y = (mt[kk] & UPPER_MASK) | (mt[kk + 1] & LOWER_MASK);
                mt[kk] = mt[kk + M] ^ (y >> 1) ^ ((y & 0x1u) == 0u ? mag01_0 : mag01_1);
            }
            for (; kk < N - 1; kk++)
            {
                y = (mt[kk] & UPPER_MASK) | (mt[kk + 1] & LOWER_MASK);
                mt[kk] = mt[kk + (M - N)] ^ (y >> 1) ^ ((y & 0x1u) == 0u ? mag01_0 : mag01_1);
            }
            y = (mt[N - 1] & UPPER_MASK) | (mt[0] & LOWER_MASK);
            mt[N - 1] = mt[M - 1] ^ (y >> 1) ^ ((y & 0x1u) == 0u ? mag01_0 : mag01_1);

            _mti = 0;
        }

        y = mt[_mti++];

        // Tempering
        y ^= (y >> 11);
        y ^= (y << 7) & 0x9D2C5680u;
        y ^= (y << 15) & 0xEFC60000u;
        y ^= (y >> 18);

        return y;
    }

    /// <inheritdoc />
    public int Next(int minInclusive, int maxExclusive)
    {
        if (minInclusive >= maxExclusive)
            throw new ArgumentOutOfRangeException(nameof(maxExclusive), "maxExclusive must be greater than minInclusive.");

        uint range = unchecked((uint)(maxExclusive - minInclusive));

        // Multiply-high method: floor((NextUInt32 * range) / 2^32) for unbiased mapping
        uint r = NextUInt32();
        uint scaled = (uint)(((ulong)r * (ulong)range) >> 32);
        return unchecked(minInclusive + (int)scaled);
    }

    /// <inheritdoc />
    public double NextDouble()
    {
        // Divide by 2^32 to get [0,1) exactly
        return NextUInt32() / 4294967296.0; // 2^32
    }
}

