using MatchEngine.Core.Engine.RNG;

namespace MatchEngine.Core.Engine.Commentary;

public sealed class CommentaryComposerFactory
{
    private readonly ICommentRepository _repo;
    private readonly string _locale;
    private readonly string _tone;
    private readonly int _cooldown;

    public CommentaryComposerFactory(ICommentRepository repo, string locale, string tone, int cooldown = 6)
    {
        _repo = repo;
        _locale = string.IsNullOrWhiteSpace(locale) ? "pl" : locale;
        _tone = string.IsNullOrWhiteSpace(tone) ? "neutral" : tone;
        _cooldown = cooldown < 0 ? 6 : cooldown;
    }

    public CommentaryComposer Create(RngStream rng) => new(rng, _repo, _locale, _tone, _cooldown);
}

