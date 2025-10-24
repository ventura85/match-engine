namespace MatchEngine.Core.Engine.Xg;

public static class XgModel
{
    // Simple monotonic model; tweakable later
    public static double ShotXg(double distanceM, double angleDeg, bool setPiece)
    {
        var baseXg = setPiece ? 0.06 : 0.08;
        var dist = Math.Clamp(distanceM, 5, 35);
        var ang = Math.Clamp(angleDeg, 5, 90);
        var dFactor = 1.2 - (dist - 5) / 40.0;     // closer → larger
        var aFactor = ang / 90.0;                  // wider angle → larger
        return Math.Clamp(baseXg * dFactor * (0.6 + 0.4 * aFactor), 0.01, 0.7);
    }
}

