using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using MatchEngine.Core.Domain.Players;
using MatchEngine.Core.Domain.Roles;
using MatchEngine.Core.Domain.Teams;

namespace MatchEngine.Core.Domain.Teams.Presets;

/// <summary>
/// Loads team presets from a directory containing JSON files. Caches in-memory.
/// </summary>
public sealed class JsonTeamRepository : ITeamRepository
{
    private readonly List<TeamPreset> _presets;

    public JsonTeamRepository(string directoryPath)
    {
        if (string.IsNullOrWhiteSpace(directoryPath))
            throw new ArgumentException("directoryPath must be provided", nameof(directoryPath));

        var dir = ResolveDirectory(directoryPath);
        if (!Directory.Exists(dir))
            throw new DirectoryNotFoundException($"Teams directory not found: {dir}");

        _presets = LoadAll(dir);
    }

    public IReadOnlyList<TeamPreset> GetPresets() => _presets;

    public TeamPreset? GetPresetById(string id)
    {
        if (string.IsNullOrWhiteSpace(id)) return null;
        return _presets.FirstOrDefault(p => string.Equals(p.Id, id, StringComparison.OrdinalIgnoreCase));
    }

    public Team? LoadTeam(string id)
    {
        var preset = GetPresetById(id);
        if (preset == null) return null;
        return MapToDomain(preset);
    }

    private static string ResolveDirectory(string path)
    {
        if (Path.IsPathRooted(path)) return path;

        // Try as-is relative to current directory
        var cwd = Directory.GetCurrentDirectory();
        var candidate = Path.GetFullPath(Path.Combine(cwd, path));
        if (Directory.Exists(candidate)) return candidate;

        // Try relative to content root (parent of bin in dev)
        var baseDir = AppContext.BaseDirectory; // bin/Debug/netX
        var tryParent1 = Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", path));
        if (Directory.Exists(tryParent1)) return tryParent1;

        // Fallback to original
        return candidate;
    }

    private static List<TeamPreset> LoadAll(string directory)
    {
        var list = new List<TeamPreset>();
        var opts = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            ReadCommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        };

        foreach (var file in Directory.EnumerateFiles(directory, "*.json", SearchOption.TopDirectoryOnly))
        {
            try
            {
                var json = File.ReadAllText(file);
                var preset = JsonSerializer.Deserialize<TeamPreset>(json, opts);
                if (preset == null) continue;
                if (string.IsNullOrWhiteSpace(preset.Id)) continue;
                list.Add(preset);
            }
            catch
            {
                // Skip malformed file silently for MVP
            }
        }

        // Stable sort by Id (LINQ is stable)
        return list.OrderBy(p => p.Id, StringComparer.Ordinal).ToList();
    }

    private static Team MapToDomain(TeamPreset p)
    {
        // Map style
        var style = ParseStyle(p.Style);
        var focus = ParseAttackFocus(p.AttackBias);

        // Build players with approximate attribute mapping from coarse values
        var srcPlayers = p.Players ?? new List<TeamPlayerPreset>();
        var players = new List<Player>(srcPlayers.Count);
        for (int i = 0; i < srcPlayers.Count; i++)
        {
            var src = srcPlayers[i];
            var attr = new Attributes();

            // Use Overall for a broad base across skills (clamped inside setters)
            int ovr = src.Overall;
            attr.Pace = ovr; attr.Accel = ovr; attr.Stamina = (int)Math.Round(Math.Clamp(src.Stamina, 0, 1) * 100);
            attr.Strength = ovr; attr.Jumping = ovr; attr.Agility = ovr; attr.Balance = ovr;
            attr.FirstTouch = ovr; attr.Dribbling = ovr; attr.Crossing = ovr; attr.ShortPass = ovr; attr.LongPass = ovr;
            attr.Finishing = ovr; attr.Heading = ovr; attr.Tackling = ovr; attr.Marking = ovr; attr.Interceptions = ovr;
            attr.SetPieces = ovr; attr.Penalties = ovr; attr.LongShots = ovr;
            attr.Vision = ovr; attr.Decision = ovr; attr.Anticipation = ovr; attr.Composure = (int)Math.Round(Math.Clamp(src.Composure, 0, 1) * 100);
            attr.OffBall = ovr; attr.Positioning = ovr; attr.Bravery = ovr; attr.Aggression = ovr; attr.Leadership = ovr; attr.Teamwork = ovr;
            attr.WorkRate = (int)Math.Round(Math.Clamp(src.WorkRate, 0, 1) * 100);

            players.Add(new Player
            {
                Id = i + 1,
                Name = string.IsNullOrWhiteSpace(src.Name) ? $"Player-{i + 1}" : src.Name,
                Foot = Footedness.Right,
                Traits = Array.Empty<Trait>(),
                Attr = attr,
                Form = 1.0,
                Energy = 1.0,
                Morale = 1.0,
            });
        }

        // Role map derived from preset order and declared roles
        var map = new Dictionary<Role, int[]>();
        foreach (Role r in Enum.GetValues(typeof(Role)))
        {
            var idxs = new List<int>();
            for (int i = 0; i < srcPlayers.Count; i++)
            {
                if (TryParseRole(srcPlayers[i].Role, out var pr) && pr == r)
                {
                    idxs.Add(i);
                }
            }
            if (idxs.Count > 0)
            {
                map[r] = idxs.ToArray();
            }
        }

        var team = new Team
        {
            Name = string.IsNullOrWhiteSpace(p.Name) ? p.Id : p.Name,
            Formation = new Formation(string.IsNullOrWhiteSpace(p.Formation) ? "4-3-3" : p.Formation),
            Tactics = new Tactics(style, Tempo.Normal, Width.Normal, LineHeight.Mid, Pressing.Med, Aggression.Med, focus, new SetPieces("short", "short")),
            Players = players,
            RoleMap = map,
        };

        return team;
    }

    private static bool TryParseRole(string? roleStr, out Role role)
    {
        role = Role.CM;
        if (string.IsNullOrWhiteSpace(roleStr)) return false;
        return Enum.TryParse<Role>(roleStr, true, out role);
    }

    private static Style ParseStyle(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return Style.Balanced;
        return s.Trim().ToLowerInvariant() switch
        {
            "attacking" => Style.Attacking,
            "defensive" => Style.Defensive,
            _ => Style.Balanced,
        };
    }

    private static AttackFocus ParseAttackFocus(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return AttackFocus.Mixed;
        return s.Trim().ToLowerInvariant() switch
        {
            "wings" => AttackFocus.Wings,
            "center" => AttackFocus.Center,
            _ => AttackFocus.Mixed,
        };
    }
}
