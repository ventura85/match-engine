using MatchEngine.Core.Domain.Roles;

namespace MatchEngine.Core.Domain.Teams;

/// <summary>
/// Formation code representation. MVP helper enforces minimal counts for key roles.
/// </summary>
/// <param name="Code">Human-readable code like 4-3-3, 4-1-4-1, 5-4-1.</param>
public readonly record struct Formation(string Code)
{
    /// <summary>
    /// For MVP validation: enforces 1 GK, at least 2 CB. Other roles are not enforced here.
    /// </summary>
    public bool RequiresAtLeast(Role role, int count)
    {
        return role switch
        {
            Role.GK => count >= 1,
            Role.CB => count >= 2,
            _ => true // other positions: no min constraint in MVP
        };
    }
}

