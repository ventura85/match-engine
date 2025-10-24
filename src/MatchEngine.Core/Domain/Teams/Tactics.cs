namespace MatchEngine.Core.Domain.Teams;

/// <summary>
/// Overall tactical style.
/// </summary>
public enum Style { Attacking, Balanced, Defensive }

/// <summary>
/// Ball tempo.
/// </summary>
public enum Tempo { Slow, Normal, Fast }

/// <summary>
/// Team width in possession.
/// </summary>
public enum Width { Narrow, Normal, Wide }

/// <summary>
/// Defensive line height.
/// </summary>
public enum LineHeight { Low, Mid, High }

/// <summary>
/// Pressing intensity.
/// </summary>
public enum Pressing { Low, Med, High }

/// <summary>
/// Defensive aggression.
/// </summary>
public enum Aggression { Low, Med, High }

/// <summary>
/// Attacking focus.
/// </summary>
public enum AttackFocus { Center, Wings, Mixed }

/// <summary>
/// Set piece preferences (simple string descriptors for MVP).
/// </summary>
/// <param name="Corners">e.g. "short"|"long"|"near-post"|"far-post"</param>
/// <param name="Freekicks">e.g. "short"|"long"</param>
public readonly record struct SetPieces(string Corners, string Freekicks);

/// <summary>
/// Team tactics configuration.
/// </summary>
/// <param name="Style">Overall style.</param>
/// <param name="Tempo">Ball tempo.</param>
/// <param name="Width">Team width.</param>
/// <param name="LineHeight">Defensive line height.</param>
/// <param name="Pressing">Pressing intensity.</param>
/// <param name="Aggression">Aggression level.</param>
/// <param name="AttackFocus">Attack focus.</param>
/// <param name="SetPieces">Set piece preferences.</param>
public readonly record struct Tactics(
    Style Style,
    Tempo Tempo,
    Width Width,
    LineHeight LineHeight,
    Pressing Pressing,
    Aggression Aggression,
    AttackFocus AttackFocus,
    SetPieces SetPieces
);

