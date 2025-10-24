using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace MatchEngine.Core.Engine.Commentary;

public sealed class JsonCommentRepository : ICommentRepository
{
    // data[locale][tone][eventType] -> list of templates
    private readonly Dictionary<string, Dictionary<string, Dictionary<string, List<string>>>> _data
        = new(StringComparer.OrdinalIgnoreCase);

    public JsonCommentRepository(string directoryPath)
    {
        if (string.IsNullOrWhiteSpace(directoryPath)) throw new ArgumentException("comments directory path required", nameof(directoryPath));
        var dir = ResolveDirectory(directoryPath);
        if (!Directory.Exists(dir)) throw new DirectoryNotFoundException($"Comments directory not found: {dir}");
        LoadAll(dir);
    }

    public IEnumerable<string> Get(string locale, string tone, string eventType)
    {
        if (string.IsNullOrWhiteSpace(locale)) locale = "pl";
        if (string.IsNullOrWhiteSpace(tone)) tone = "neutral";
        var key = eventType ?? string.Empty;

        if (_data.TryGetValue(locale, out var byTone))
        {
            if (byTone.TryGetValue(tone, out var map) && map.TryGetValue(key, out var list) && list.Count > 0)
            {
                return list;
            }
            // fallback to neutral
            if (!tone.Equals("neutral", StringComparison.OrdinalIgnoreCase) &&
                byTone.TryGetValue("neutral", out var neut) && neut.TryGetValue(key, out var listN) && listN.Count > 0)
            {
                return listN;
            }
        }
        return Array.Empty<string>();
    }

    private static string ResolveDirectory(string path)
    {
        if (Path.IsPathRooted(path)) return path;
        var cwd = Directory.GetCurrentDirectory();
        var candidate = Path.GetFullPath(Path.Combine(cwd, path));
        if (Directory.Exists(candidate)) return candidate;
        var baseDir = AppContext.BaseDirectory;
        // try ascending up to 6 levels from base directory
        string up = baseDir;
        for (int i = 0; i < 6; i++)
        {
            up = Path.GetFullPath(Path.Combine(up, ".."));
            var p = Path.GetFullPath(Path.Combine(up, path));
            if (Directory.Exists(p)) return p;
        }
        return candidate;
    }

    private void LoadAll(string baseDir)
    {
        var opts = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };

        // Determine locale directories
        var localeDirs = Directory.EnumerateDirectories(baseDir).ToList();
        if (localeDirs.Count == 0)
        {
            // Treat baseDir as single-locale folder named by last segment
            localeDirs = new List<string> { baseDir };
        }

        foreach (var locDir in localeDirs)
        {
            var locale = new DirectoryInfo(locDir).Name;
            foreach (var file in Directory.EnumerateFiles(locDir, "*.json", SearchOption.TopDirectoryOnly))
            {
                string tone = Path.GetFileNameWithoutExtension(file);
                try
                {
                    var json = File.ReadAllText(file);
                    var doc = JsonSerializer.Deserialize<Dictionary<string, string[]>>(json, opts);
                    if (doc == null) continue;
                    if (!_data.TryGetValue(locale, out var byTone))
                    {
                        byTone = new Dictionary<string, Dictionary<string, List<string>>>(StringComparer.OrdinalIgnoreCase);
                        _data[locale] = byTone;
                    }
                    if (!byTone.TryGetValue(tone, out var map))
                    {
                        map = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
                        byTone[tone] = map;
                    }

                    foreach (var kv in doc)
                    {
                        var ev = kv.Key; // expect EventType name, e.g., "Goal"
                        var vals = kv.Value?.Where(s => !string.IsNullOrWhiteSpace(s)).Select(s => s.Trim()).ToArray() ?? Array.Empty<string>();
                        if (!map.TryGetValue(ev, out var list))
                        {
                            list = new List<string>();
                            map[ev] = list;
                        }
                        list.AddRange(vals);
                    }
                }
                catch
                {
                    // ignore malformed
                }
            }
        }
    }
}
