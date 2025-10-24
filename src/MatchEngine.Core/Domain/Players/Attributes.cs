using System;
using System.Collections.Generic;

namespace MatchEngine.Core.Domain.Players;

/// <summary>
/// Player attributes grouped by Physical, Technical, and Mental skill sets.
/// Each attribute is in range [0,100].
/// </summary>
public class Attributes
{
    private static int Clamp(int v) => v < 0 ? 0 : (v > 100 ? 100 : v);

    // Physical
    private int _pace;          public int Pace { get => _pace; set => _pace = Clamp(value); }
    private int _accel;         public int Accel { get => _accel; set => _accel = Clamp(value); }
    private int _stamina;       public int Stamina { get => _stamina; set => _stamina = Clamp(value); }
    private int _strength;      public int Strength { get => _strength; set => _strength = Clamp(value); }
    private int _jumping;       public int Jumping { get => _jumping; set => _jumping = Clamp(value); }
    private int _agility;       public int Agility { get => _agility; set => _agility = Clamp(value); }
    private int _balance;       public int Balance { get => _balance; set => _balance = Clamp(value); }

    // Technical
    private int _firstTouch;    public int FirstTouch { get => _firstTouch; set => _firstTouch = Clamp(value); }
    private int _dribbling;     public int Dribbling { get => _dribbling; set => _dribbling = Clamp(value); }
    private int _crossing;      public int Crossing { get => _crossing; set => _crossing = Clamp(value); }
    private int _shortPass;     public int ShortPass { get => _shortPass; set => _shortPass = Clamp(value); }
    private int _longPass;      public int LongPass { get => _longPass; set => _longPass = Clamp(value); }
    private int _finishing;     public int Finishing { get => _finishing; set => _finishing = Clamp(value); }
    private int _heading;       public int Heading { get => _heading; set => _heading = Clamp(value); }
    private int _tackling;      public int Tackling { get => _tackling; set => _tackling = Clamp(value); }
    private int _marking;       public int Marking { get => _marking; set => _marking = Clamp(value); }
    private int _interceptions; public int Interceptions { get => _interceptions; set => _interceptions = Clamp(value); }
    private int _setPieces;     public int SetPieces { get => _setPieces; set => _setPieces = Clamp(value); }
    private int _penalties;     public int Penalties { get => _penalties; set => _penalties = Clamp(value); }
    private int _longShots;     public int LongShots { get => _longShots; set => _longShots = Clamp(value); }

    // Mental
    private int _vision;        public int Vision { get => _vision; set => _vision = Clamp(value); }
    private int _decision;      public int Decision { get => _decision; set => _decision = Clamp(value); }
    private int _anticipation;  public int Anticipation { get => _anticipation; set => _anticipation = Clamp(value); }
    private int _composure;     public int Composure { get => _composure; set => _composure = Clamp(value); }
    private int _offBall;       public int OffBall { get => _offBall; set => _offBall = Clamp(value); }
    private int _positioning;   public int Positioning { get => _positioning; set => _positioning = Clamp(value); }
    private int _bravery;       public int Bravery { get => _bravery; set => _bravery = Clamp(value); }
    private int _aggression;    public int Aggression { get => _aggression; set => _aggression = Clamp(value); }
    private int _leadership;    public int Leadership { get => _leadership; set => _leadership = Clamp(value); }
    private int _teamwork;      public int Teamwork { get => _teamwork; set => _teamwork = Clamp(value); }
    private int _workRate;      public int WorkRate { get => _workRate; set => _workRate = Clamp(value); }

    /// <summary>
    /// Creates attributes with all values defaulting to 50.
    /// </summary>
    public Attributes()
    {
        Pace = Accel = Stamina = Strength = Jumping = Agility = Balance = 50;
        FirstTouch = Dribbling = Crossing = ShortPass = LongPass = Finishing = Heading = Tackling = Marking = Interceptions = SetPieces = Penalties = LongShots = 50;
        Vision = Decision = Anticipation = Composure = OffBall = Positioning = Bravery = Aggression = Leadership = Teamwork = WorkRate = 50;
    }

    /// <summary>
    /// Returns a map of all skills by exact name to their numeric values.
    /// </summary>
    public Dictionary<string, double> ToSkillMap() => new()
    {
        // Physical
        ["Pace"] = Pace,
        ["Accel"] = Accel,
        ["Stamina"] = Stamina,
        ["Strength"] = Strength,
        ["Jumping"] = Jumping,
        ["Agility"] = Agility,
        ["Balance"] = Balance,

        // Technical
        ["FirstTouch"] = FirstTouch,
        ["Dribbling"] = Dribbling,
        ["Crossing"] = Crossing,
        ["ShortPass"] = ShortPass,
        ["LongPass"] = LongPass,
        ["Finishing"] = Finishing,
        ["Heading"] = Heading,
        ["Tackling"] = Tackling,
        ["Marking"] = Marking,
        ["Interceptions"] = Interceptions,
        ["SetPieces"] = SetPieces,
        ["Penalties"] = Penalties,
        ["LongShots"] = LongShots,

        // Mental
        ["Vision"] = Vision,
        ["Decision"] = Decision,
        ["Anticipation"] = Anticipation,
        ["Composure"] = Composure,
        ["OffBall"] = OffBall,
        ["Positioning"] = Positioning,
        ["Bravery"] = Bravery,
        ["Aggression"] = Aggression,
        ["Leadership"] = Leadership,
        ["Teamwork"] = Teamwork,
        ["WorkRate"] = WorkRate,
    };
}

