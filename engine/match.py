"""Główny silnik meczowy - symulacja 10 minut (5 min każda połowa)."""
import random
import time
from typing import Dict, List, Tuple, Optional
from models.team import Team
from models.player import Player
from engine.duel import DuelSystem
from engine.utils import calculate_team_strength


class MatchEngine:
    """
    Silnik symulacji meczu piłkarskiego.
    
    Symuluje 10 minut meczu w czasie rzeczywistym (5 min każda połowa).
    Mecz dzieli się na 10 ticków (1 tick = 1 minuta symulacji).
    """
    
    def __init__(self, team_a: Team, team_b: Team, verbose: bool = True, real_time: bool = False):
        """
        Inicjalizuje silnik meczu.
        
        Args:
            team_a: Pierwsza drużyna
            team_b: Druga drużyna
            verbose: Czy wypisywać szczegółowe komentarze
            real_time: Czy mecz ma trwać 10 minut czasu rzeczywistego (False = natychmiast)
        """
        self.team_a = team_a
        self.team_b = team_b
        self.verbose = verbose
        self.real_time = real_time
        
        self.duel_system = DuelSystem(verbose=verbose)
        
        # Stan meczu
        self.score_a = 0
        self.score_b = 0
        self.events: List[Dict] = []
        self.possession_a = 0
        self.possession_b = 0
        self.shots_a = 0
        self.shots_b = 0
        self.shots_on_target_a = 0
        self.shots_on_target_b = 0
        self.substitutions = []
        self.current_minute = 0
        
        # Oblicz siłę drużyn
        self.strength_a = calculate_team_strength(team_a)
        self.strength_b = calculate_team_strength(team_b)
    
    def print_lineups(self):
        """Wyświetla składy obu drużyn przed meczem."""
        print("\n" + "="*80)
        print(f"⚽ SKŁADY DRUŻYN ⚽")
        print("="*80)
        
        # Drużyna A
        print(f"\n🔴 {self.team_a.name.upper()}")
        print(f"   Formacja: {self.team_a.formation} | Styl: {self.team_a.style} | Atak: {self.team_a.attack_channel}")
        print(f"   Siła: Atak {self.strength_a['attack']:.1f} | Obrona {self.strength_a['defense']:.1f} | Kontrola {self.strength_a['control']:.1f}")
        print("\n   Skład:")
        
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            players = [p for p in self.team_a.players if p.position == pos]
            if players:
                pos_name = {'GK': 'Bramkarz', 'DEF': 'Obrońcy', 'MID': 'Pomocnicy', 'FWD': 'Napastnicy'}[pos]
                print(f"\n   {pos_name}:")
                for p in players:
                    overall = p.get_overall_rating()
                    traits_str = ', '.join(p.traits[:2]) if p.traits else '-'
                    print(f"      #{p.id:2d} {p.name:25s} | Overall: {overall:4.1f} | Forma: {p.form:.2f} | Cechy: {traits_str}")
        
        # Drużyna B
        print(f"\n🔵 {self.team_b.name.upper()}")
        print(f"   Formacja: {self.team_b.formation} | Styl: {self.team_b.style} | Atak: {self.team_b.attack_channel}")
        print(f"   Siła: Atak {self.strength_b['attack']:.1f} | Obrona {self.strength_b['defense']:.1f} | Kontrola {self.strength_b['control']:.1f}")
        print("\n   Skład:")
        
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            players = [p for p in self.team_b.players if p.position == pos]
            if players:
                pos_name = {'GK': 'Bramkarz', 'DEF': 'Obrońcy', 'MID': 'Pomocnicy', 'FWD': 'Napastnicy'}[pos]
                print(f"\n   {pos_name}:")
                for p in players:
                    overall = p.get_overall_rating()
                    traits_str = ', '.join(p.traits[:2]) if p.traits else '-'
                    print(f"      #{p.id:2d} {p.name:25s} | Overall: {overall:4.1f} | Forma: {p.form:.2f} | Cechy: {traits_str}")
        
        print("\n" + "="*80 + "\n")
    
    def simulate_match(self) -> Dict:
        """
        Symuluje cały mecz (10 minut: 5 min + 5 min).
        
        Returns:
            Słownik z wynikami meczu i statystykami
        """
        # Wyświetl składy przed meczem
        self.print_lineups()
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"🏟️  ROZPOCZĘCIE MECZU: {self.team_a.name} vs {self.team_b.name}")
            print(f"{'='*80}\n")
            time.sleep(1 if self.real_time else 0)
        
        # Pierwsza połowa (5 minut)
        print(f"⏱️  PIERWSZA POŁOWA\n")
        self.simulate_half(1, 5)
        
        # Przerwa i możliwe zmiany
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"⏸️  PRZERWA - Wynik: {self.team_a.name} {self.score_a}:{self.score_b} {self.team_b.name}")
            print(f"{'='*80}\n")
            time.sleep(2 if self.real_time else 0)
        
        # Losowe zmiany w przerwie
        self._make_halftime_substitutions()
        
        # Druga połowa (5 minut)
        print(f"⏱️  DRUGA POŁOWA\n")
        self.simulate_half(6, 10)
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"🏁 KONIEC MECZU!")
            print(f"{'='*80}\n")
        
        return self.generate_report()
    
    def _make_halftime_substitutions(self):
        """Wykonuje zmiany w przerwie (losowe, 30% szans) - symulowane."""
        if random.random() < 0.3:  # 30% szans na zmianę
            team = random.choice([self.team_a, self.team_b])
            team_name = team.name
            
            # Wybierz zawodnika do zmiany (nie bramkarza, nie najlepszego)
            candidates = [p for p in team.players if not p.is_goalkeeper()]
            if len(candidates) > 1:
                # Zmień zawodnika z niższą formą
                candidates.sort(key=lambda p: p.form)
                player_out = candidates[0]
                
                # Symuluj zmianę - zmniejsz formę "wymienionego" zawodnika
                # (w pełnej wersji tutaj byłby zawodnik z ławki)
                player_out.form = max(0.5, player_out.form * 0.8)
                
                print(f"🔄 ZMIANA TAKTYCZNA - {team_name}: {player_out.name} zmniejsza aktywność")
                print(f"   💡 Trener wprowadza zmiany taktyczne\n")
                
                self.substitutions.append({
                    'minute': 'Przerwa',
                    'team': team_name,
                    'player_out': player_out.name,
                    'reason': 'taktyczna - zmiana ustawienia'
                })
    
    def simulate_half(self, start_minute: int, end_minute: int) -> None:
        """
        Symuluje połowę meczu.
        
        Args:
            start_minute: Początkowa minuta (1-5 lub 6-10)
            end_minute: Końcowa minuta (5 lub 10)
        """
        # Każda połowa = 5 minut
        for minute in range(start_minute, end_minute + 1):
            self.current_minute = minute
            
            if self.real_time:
                time.sleep(60)  # Rzeczywista minuta
            
            # Symuluj kilka akcji w każdej minucie
            num_actions = random.randint(3, 6)  # 3-6 akcji na minutę
            
            for _ in range(num_actions):
                self.simulate_action(minute)
    
    def simulate_action(self, minute: int) -> None:
        """
        Symuluje pojedynczą akcję w meczu.
        
        Args:
            minute: Numer minuty
        """
        # Określ która drużyna ma posiadanie
        attacking_team, defending_team = self._determine_possession()
        
        # Zwiększ licznik posiadania
        if attacking_team == self.team_a:
            self.possession_a += 1
        else:
            self.possession_b += 1
        
        # WPŁYW TAKTYKI - modyfikuj szanse na akcję
        attack_rating = attacking_team.get_attack_rating()
        defense_rating = defending_team.get_defense_rating()
        
        # Styl atakujący = więcej akcji ofensywnych
        style_modifier = 1.5 if attacking_team.style == 'attacking' else 1.0
        style_modifier = 0.7 if attacking_team.style == 'defensive' else style_modifier
        
        # Bazowa szansa na akcję ofensywną
        action_chance = (0.15 + (attack_rating / 800.0)) * style_modifier
        
        if random.random() < action_chance:
            action_type = random.choice(['pass', 'dribble', 'shot'])
            
            if action_type == 'shot':
                self._simulate_shot_action(minute, attacking_team, defending_team)
            elif action_type == 'dribble':
                self._simulate_dribble_action(minute, attacking_team, defending_team)
            else:
                self._simulate_pass_action(minute, attacking_team)
    
    def _simulate_pass_action(self, minute: int, team: Team):
        """Symuluje podanie."""
        player = team.get_random_outfield_player()
        
        if self.verbose and random.random() < 0.15:  # 15% szans na komentarz
            print(f"  {minute}' - {player.name} ({team.name}) rozgrywa piłkę...")
    
    def _simulate_dribble_action(self, minute: int, attacking_team: Team, defending_team: Team):
        """Symuluje drybling."""
        attacker = attacking_team.get_random_outfield_player()
        defender = defending_team.get_random_outfield_player()
        
        attacker_skill = attacker.get_overall_rating()
        defender_skill = defender.get_overall_rating()
        
        # Taktyka wpływa na drybling
        if attacking_team.attack_channel == 'wings':
            attacker_skill *= 1.1  # Bonus na skrzydłach
        
        success = attacker_skill > defender_skill + random.randint(-15, 15)
        
        if success and self.verbose:
            print(f"  {minute}' - ✨ {attacker.name} ({attacking_team.name}) świetny drybling! Mija {defender.name}!")
        elif self.verbose and random.random() < 0.2:
            print(f"  {minute}' - {defender.name} ({defending_team.name}) odbiera piłkę {attacker.name}")
    
    def _simulate_shot_action(self, minute: int, attacking_team: Team, defending_team: Team):
        """Symuluje strzał na bramkę."""
        shooter = attacking_team.get_random_outfield_player()
        goalkeeper = defending_team.get_goalkeeper()
        
        # Statystyki strzału
        if attacking_team == self.team_a:
            self.shots_a += 1
        else:
            self.shots_b += 1
        
        # Oblicz szansę na celność (WPŁYW TAKTYKI!)
        shooter_rating = shooter.get_overall_rating()
        
        # Styl atakujący = lepsze strzały
        if attacking_team.style == 'attacking':
            shooter_rating *= 1.15
        
        on_target_chance = shooter_rating / 140.0
        on_target_chance = max(0.3, min(0.85, on_target_chance))
        
        if random.random() < on_target_chance:
            # Celny strzał!
            if attacking_team == self.team_a:
                self.shots_on_target_a += 1
            else:
                self.shots_on_target_b += 1
            
            # Szansa na gola
            gk_rating = goalkeeper.get_overall_rating() if goalkeeper else 60
            
            # Obrona defensywna = lepsi bramkarze
            if defending_team.style == 'defensive':
                gk_rating *= 1.1
            
            goal_chance = 0.25 + (shooter_rating - gk_rating) / 250.0
            goal_chance = max(0.10, min(0.55, goal_chance))
            
            if random.random() < goal_chance:
                # GOOOOOL!
                if attacking_team == self.team_a:
                    self.score_a += 1
                else:
                    self.score_b += 1
                
                print(f"\n{'🔥'*30}")
                print(f"⚽⚽⚽ {minute}' - GOOOOOOL!!!! {shooter.name} ({attacking_team.name})! ⚽⚽⚽")
                print(f"  Wspaniały strzał! {shooter.name} pokonuje bramkarza!")
                print(f"  Wynik: {self.team_a.name} {self.score_a}:{self.score_b} {self.team_b.name}")
                print(f"{'🔥'*30}\n")
                
                self.events.append({
                    'minute': minute,
                    'team': attacking_team.name,
                    'players': [shooter.name],
                    'event_type': 'goal',
                    'description': f'GOL! {shooter.name}'
                })
            else:
                # Obrona bramkarza
                gk_name = goalkeeper.name if goalkeeper else "bramkarz"
                print(f"  {minute}' - 🧤 Strzał {shooter.name} ({attacking_team.name}) - OBRONA {gk_name}! Wielka parada!")
                
                self.events.append({
                    'minute': minute,
                    'team': attacking_team.name,
                    'players': [shooter.name, gk_name],
                    'event_type': 'shot_saved',
                    'description': f'Obrona {gk_name}'
                })
        else:
            # Niecelny strzał
            if self.verbose:
                print(f"  {minute}' - ❌ {shooter.name} ({attacking_team.name}) strzela niecelnie! Obok bramki!")
            
            self.events.append({
                'minute': minute,
                'team': attacking_team.name,
                'players': [shooter.name],
                'event_type': 'shot_off_target',
                'description': f'Niecelny strzał {shooter.name}'
            })
    
    def _determine_possession(self) -> Tuple[Team, Team]:
        """
        Określa która drużyna ma posiadanie piłki.
        WPŁYW TAKTYKI: kontrola i styl gry mają znaczenie!
        
        Returns:
            Tuple (attacking_team, defending_team)
        """
        control_a = self.strength_a['control']
        control_b = self.strength_b['control']
        
        # Modyfikatory taktyczne
        if self.team_a.style == 'attacking':
            control_a *= 1.1
        elif self.team_a.style == 'defensive':
            control_a *= 0.9
        
        if self.team_b.style == 'attacking':
            control_b *= 1.1
        elif self.team_b.style == 'defensive':
            control_b *= 0.9
        
        # Normalizuj do prawdopodobieństwa
        total_control = control_a + control_b
        prob_a = control_a / total_control if total_control > 0 else 0.5
        
        if random.random() < prob_a:
            return self.team_a, self.team_b
        else:
            return self.team_b, self.team_a
    
    def generate_report(self) -> Dict:
        """
        Generuje raport z meczu.
        
        Returns:
            Słownik z pełnymi statystykami meczu
        """
        total_possession = self.possession_a + self.possession_b
        
        report = {
            'team_a': self.team_a.name,
            'team_b': self.team_b.name,
            'score': (self.score_a, self.score_b),
            'possession': {
                self.team_a.name: round((self.possession_a / total_possession * 100) if total_possession > 0 else 50, 1),
                self.team_b.name: round((self.possession_b / total_possession * 100) if total_possession > 0 else 50, 1)
            },
            'shots': {
                self.team_a.name: self.shots_a,
                self.team_b.name: self.shots_b
            },
            'shots_on_target': {
                self.team_a.name: self.shots_on_target_a,
                self.team_b.name: self.shots_on_target_b
            },
            'events': self.events,
            'goals': self._extract_goals(),
            'substitutions': self.substitutions,
            'tactical_impact': self._analyze_tactical_impact()
        }
        
        return report
    
    def _extract_goals(self) -> List[Dict]:
        """Wyciąga listę goli z eventów."""
        goals = []
        for event in self.events:
            if event['event_type'] == 'goal':
                goals.append({
                    'minute': event['minute'],
                    'team': event['team'],
                    'scorer': event.get('scorer', event['players'][0] if event['players'] else 'Unknown'),
                    'description': event['description']
                })
        return goals
    
    def _analyze_tactical_impact(self) -> Dict:
        """Analizuje wpływ taktyki na wynik meczu."""
        analysis = {
            'team_a_style': self.team_a.style,
            'team_b_style': self.team_b.style,
            'possession_difference': abs(self.possession_a - self.possession_b),
            'shots_efficiency_a': round((self.shots_on_target_a / self.shots_a * 100) if self.shots_a > 0 else 0, 1),
            'shots_efficiency_b': round((self.shots_on_target_b / self.shots_b * 100) if self.shots_b > 0 else 0, 1),
        }
        return analysis
