using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using FluentAssertions;
using Xunit;

namespace MatchEngine.Tests;

public class CommentAssetsShapeTests
{
    private static readonly string FunPath = ResolvePath(Path.Combine("assets","comments","pl","fun.json"));
    private static readonly string NeutralPath = ResolvePath(Path.Combine("assets","comments","pl","neutral.json"));

    private static readonly string[] KeyEvents = new[]
    {
        "Kickoff","Goal","SaveMade","ShotOnTarget","FreekickAwarded","CornerAwarded","FoulCommitted","YellowCard","RedCard","PenaltyAwarded","HalfTime","FinalWhistle"
    };
    private static readonly string[] MicroEvents = new[] { "BuildUp","FinalThird","DuelWon","DuelLost" };

    [Fact]
    public void Every_bucket_has_minimum_count_and_diacritics_ratio()
    {
        var fun = Read(FunPath);
        var neu = Read(NeutralPath);

        foreach (var isFun in new[] { true, false })
        {
            var doc = isFun ? fun : neu;
            foreach (var ev in KeyEvents)
            {
                doc.Should().ContainKey(ev);
                var list = doc[ev];
                list.Should().NotBeNull();
                int min = ev == "Goal" ? 35 : 25;
                list!.Count.Should().BeGreaterOrEqualTo(min);
                list.Should().OnlyContain(s => !string.IsNullOrWhiteSpace(s));
                list.Should().OnlyContain(s => s == s.Trim());
                AtLeastDiacritics(list, 0.30);
            }
            foreach (var ev in MicroEvents)
            {
                doc.Should().ContainKey(ev);
                var list = doc[ev];
                list.Should().NotBeNull();
                list!.Count.Should().BeGreaterOrEqualTo(18);
                list.Should().OnlyContain(s => !string.IsNullOrWhiteSpace(s));
                list.Should().OnlyContain(s => s == s.Trim());
                AtLeastDiacritics(list, 0.30);
            }
        }
    }

    private static Dictionary<string,List<string>> Read(string path)
    {
        var json = File.ReadAllText(path);
        var d = JsonSerializer.Deserialize<Dictionary<string, List<string>>>(json, new JsonSerializerOptions{PropertyNameCaseInsensitive=true});
        return d!;
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

    private static void AtLeastDiacritics(IEnumerable<string> lines, double ratio)
    {
        var rx = new Regex("[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]", RegexOptions.Compiled);
        int total = 0, with = 0;
        foreach (var s in lines)
        {
            total++;
            if (rx.IsMatch(s)) with++;
        }
        (with / (double)total).Should().BeGreaterOrEqualTo(ratio);
    }
}
