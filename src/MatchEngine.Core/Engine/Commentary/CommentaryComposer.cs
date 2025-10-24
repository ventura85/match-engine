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
    private readonly CommentaryPolicy _policy;
    private readonly Queue<string> _recent = new();
    private readonly HashSet<string> _recentSet = new(StringComparer.Ordinal);
    private readonly HashSet<int> _microMinutes = new();
    private int _lastMicroEventIndex = int.MinValue;
    private int _seqCounter = -1; // used by TryComposeMicro() overload without index
    private static readonly Regex Placeholder = new("\u007B(minute|team|opponent)\u007D", RegexOptions.Compiled | RegexOptions.CultureInvariant);

    public CommentaryComposer(RngStream commentaryRng, ICommentRepository repo, string locale = "pl", string tone = "neutral", int cooldownSize = 6, CommentaryPolicy? policy = null)
    {
        _rng = commentaryRng ?? throw new ArgumentNullException(nameof(commentaryRng));
        _repo = repo ?? throw new ArgumentNullException(nameof(repo));
        _cooldownSize = Math.Max(0, cooldownSize);
        _locale = string.IsNullOrWhiteSpace(locale) ? "pl" : locale;
        _tone = string.IsNullOrWhiteSpace(tone) ? "neutral" : tone;
        _policy = policy ?? new CommentaryPolicy();
    }

    public string Compose(string eventType, int minute, string team, string opponent)
    {
        var templates = _repo.Get(_locale, _tone, eventType).ToList();
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

    // Overload that advances internal sequence index automatically (used only if caller cannot provide index)
    public string? TryComposeMicro(string eventType, int minute, string team, string opponent)
    {
        _seqCounter++;
        return TryComposeMicro(eventType, minute, team, opponent, _seqCounter);
    }

    public string? TryComposeMicro(string eventType, int minute, string team, string opponent, int eventIndex)
    {
        double p = eventType switch
        {
            "BuildUp" => _policy.BuildUpProb,
            "FinalThird" => _policy.FinalThirdProb,
            "DuelWon" => _policy.DuelWonProb,
            "DuelLost" => _policy.DuelLostProb,
            _ => -1.0
        };
        if (p < 0) return null; // not a micro event

        if (_microMinutes.Contains(minute)) return null; // max per minute enforced for micro
        if (_lastMicroEventIndex != int.MinValue && eventIndex - _lastMicroEventIndex < _policy.GlobalCooldownEvents)
            return null;

        // probability gate (consume RNG deterministically regardless of outcome)
        var roll = _rng.NextDouble();
        if (!(roll < p)) return null;

        // select template with cooldown avoidance
        var templates = _repo.Get(_locale, _tone, eventType).ToList();
        if (templates.Count == 0)
        {
            templates = _repo.Get(_locale, "neutral", eventType).ToList();
            if (templates.Count == 0) return null;
        }

        string? chosen = null;
        for (int attempt = 0; attempt < 4; attempt++)
        {
            int idx = _rng.Next(0, templates.Count);
            var cand = templates[idx];
            if (!_recentSet.Contains(cand)) { chosen = cand; break; }
        }
        chosen ??= templates.FirstOrDefault(t => !_recentSet.Contains(t)) ?? templates[0];

        // push into cooldown tracking
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

        _microMinutes.Add(minute);
        _lastMicroEventIndex = eventIndex;

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
