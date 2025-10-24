using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using MatchEngine.Core.Engine.RNG;

namespace MatchEngine.Core.Engine.Commentary;

public sealed class CommentaryComposer
{
    private readonly RngStream _rng;
    private readonly ICommentRepository _repo;
    private readonly int _cooldownSize;
    private readonly string _locale;
    private readonly string _tone;
    private readonly Queue<string> _recent = new();
    private readonly HashSet<string> _recentSet = new(StringComparer.Ordinal);
    private static readonly Regex Placeholder = new("\u007B(minute|team|opponent)\u007D", RegexOptions.Compiled | RegexOptions.CultureInvariant);

    public CommentaryComposer(RngStream commentaryRng, ICommentRepository repo, string locale = "pl", string tone = "neutral", int cooldownSize = 6)
    {
        _rng = commentaryRng ?? throw new ArgumentNullException(nameof(commentaryRng));
        _repo = repo ?? throw new ArgumentNullException(nameof(repo));
        _cooldownSize = Math.Max(0, cooldownSize);
        _locale = string.IsNullOrWhiteSpace(locale) ? "pl" : locale;
        _tone = string.IsNullOrWhiteSpace(tone) ? "neutral" : tone;
    }

    public string Compose(string eventType, int minute, string team, string opponent)
    {
        var templates = _repo.Get(_locale, _tone, eventType).ToList();
        if (templates.Count == 0)
        {
            templates = _repo.Get(_locale, "neutral", eventType).ToList();
        }
        // If pool is still small, enrich with kickoff lines to improve variety
        if (templates.Count < 5)
        {
            var extra = _repo.Get(_locale, _tone, "Kickoff").Concat(_repo.Get(_locale, "neutral", "Kickoff"));
            templates = templates.Concat(extra).Distinct().ToList();
        }
        if (templates.Count == 0)
        {
            return string.Empty;
        }

        string? chosen = null;
        for (int attempt = 0; attempt < 4; attempt++)
        {
            int idx = _rng.Next(0, templates.Count);
            var cand = templates[idx];
            if (!_recentSet.Contains(cand))
            {
                chosen = cand; break;
            }
        }
        if (chosen is null)
        {
            chosen = templates.FirstOrDefault(t => !_recentSet.Contains(t)) ?? templates[0];
        }

        // push to cooldown
        if (_cooldownSize > 0)
        {
            _recent.Enqueue(chosen);
            _recentSet.Add(chosen);
            while (_recent.Count > _cooldownSize)
            {
                var old = _recent.Dequeue();
                _recentSet.Remove(old);
            }
        }

        return Placeholder.Replace(chosen, m =>
        {
            var key = m.Groups[1].Value;
            return key switch
            {
                "minute" => minute.ToString(),
                "team" => team ?? string.Empty,
                "opponent" => opponent ?? string.Empty,
                _ => m.Value
            };
        });
    }
}
