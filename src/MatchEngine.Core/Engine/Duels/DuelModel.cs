namespace MatchEngine.Core.Engine.Duels;

public static class DuelModel
{
    /// <summary>Returns win probability for attacker in [0,1].</summary>
    public static double AttackerWinProb(
        double attStrength, double attBalance, double attWorkRate, double attAggression,
        double defStrength, double defBalance, double defWorkRate, double defAggression,
        double fatigueFactor)
    {
        // Simple logistic on weighted attribute difference + fatigue.
        double att = 0.35 * attStrength + 0.25 * attBalance + 0.20 * attWorkRate + 0.20 * attAggression;
        double def = 0.35 * defStrength + 0.25 * defBalance + 0.20 * defWorkRate + 0.20 * defAggression;
        double delta = (att - def) * fatigueFactor; // tired attacker -> lower delta
        // map delta [-50..50] -> prob ~ [0.1..0.9]
        double p = 1.0 / (1.0 + Math.Exp(-delta / 8.0));
        return Math.Clamp(p, 0.1, 0.9);
    }
}

