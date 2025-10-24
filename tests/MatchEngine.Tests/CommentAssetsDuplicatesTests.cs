using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace MatchEngine.Tests;

public class CommentAssetsDuplicatesTests
{
    private static readonly string FunPath = ResolvePath(Path.Combine("assets","comments","pl","fun.json"));
    private static readonly string NeutralPath = ResolvePath(Path.Combine("assets","comments","pl","neutral.json"));

    [Fact]
    public void No_duplicates_per_bucket_when_normalized()
    {
        foreach (var path in new[]{FunPath, NeutralPath})
        {
            var doc = Read(path);
            foreach (var (key, list) in doc)
            {
                var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (var raw in list)
                {
                    var norm = Normalize(raw);
                    set.Add(norm).Should().BeTrue($"duplicate in {Path.GetFileName(path)} event {key}: {raw}");
                }
            }
        }
    }

    private static Dictionary<string,List<string>> Read(string path)
    {
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<Dictionary<string, List<string>>>(json)!;
    }

    private static string ResolvePath(string relative)
    {
        var dir = AppContext.BaseDirectory;
        for (int i = 0; i < 8; i++)
        {
            var p = Path.GetFullPath(Path.Combine(dir, relative));
            if (File.Exists(p)) return p;
            dir = Path.GetFullPath(Path.Combine(dir, ".."));
        }
        return relative;
    }

    private static string Normalize(string s)
    {
        var trimmed = string.Join(' ', s.Trim().Split(new[]{' ','\t'}, StringSplitOptions.RemoveEmptyEntries));
        string formD = trimmed.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(formD.Length);
        foreach (var ch in formD)
        {
            var uc = CharUnicodeInfo.GetUnicodeCategory(ch);
            if (uc != UnicodeCategory.NonSpacingMark)
                sb.Append(char.ToLowerInvariant(ch));
        }
        return sb.ToString().Normalize(NormalizationForm.FormC);
    }
}
