using System.Collections.Generic;

namespace MatchEngine.Core.Domain.Teams.Presets;

public interface ITeamRepository
{
    /// <summary>
    /// Returns all presets sorted stably by Id (deterministic).
    /// </summary>
    IReadOnlyList<TeamPreset> GetPresets();

    /// <summary>
    /// Finds a preset by id (case-insensitive). Returns null when not found.
    /// </summary>
    TeamPreset? GetPresetById(string id);

    /// <summary>
    /// Builds a playable Team from a preset id. Returns null if not found or invalid.
    /// </summary>
    Team? LoadTeam(string id);
}

