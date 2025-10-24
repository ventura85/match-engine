namespace MatchEngine.Core.Engine.Gk;

public static class GkModel
{
    /// <summary>Returns save probability in [0,1] for a shot on target.</summary>
    public static double SaveProbability(
        double xg,
        double gkAgility,
        double gkPositioning,
        double gkComposure,
        double distanceM, double angleDeg)
    {
        // MVP: better GK & worse xG -> higher save probability.
        // Base conversion: goalProb ~= clamp(xg*0.9, 0.05, 0.85)
        var goalProb = Math.Clamp(xg * 0.9, 0.05, 0.85);
        // GK quality factor in [0.8..1.2] roughly:
        double gkQ = 0.8 + (gkAgility + gkPositioning + gkComposure) / 300.0 * 0.4;
        // Angle/distance slight easing for GK (tighter angle, longer distance => easier save):
        var d = Math.Clamp(distanceM, 5, 35);
        var a = Math.Clamp(angleDeg, 5, 90);
        double geom = ((d - 5) / 30.0 * 0.15) + ((90 - a) / 85.0 * 0.15); // up to +0.3 to save chance
        var saveProb = Math.Clamp((1 - goalProb) * gkQ + geom, 0.05, 0.95);
        return saveProb;
    }
}

