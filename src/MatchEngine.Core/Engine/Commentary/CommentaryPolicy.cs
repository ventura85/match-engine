namespace MatchEngine.Core.Engine.Commentary;

public record CommentaryPolicy(
    double BuildUpProb = 0.05,
    double FinalThirdProb = 0.08,
    double DuelWonProb = 0.06,
    double DuelLostProb = 0.06,
    int GlobalCooldownEvents = 2,
    int MaxPerMinute = 1
);
