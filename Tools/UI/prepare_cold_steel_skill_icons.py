"""Restore the selected Cold Steel skill icons from their local authoring sources."""
from pathlib import Path
import shutil

PROJECT = Path(__file__).resolve().parents[2]
RUNTIME = PROJECT / "Content/ColdSteelData/Skills"
ICONS = {
    "whirlwind_cold_steel.png": "SourceAssets/Whirlwind20260920/whirlwind_cold_steel.png",
    "heavy_strike_cold_steel.png": "SourceAssets/HeavyStrike20260914/heavy_strike_cold_steel.png",
    "fireball_ember_red.png": "SourceAssets/Fireball20260914/IconEmberRed/fireball_ember_red.png",
    "ice_spike_cold_steel.png": "SourceAssets/IceSpike20260915/ice_spike_cold_steel.png",
    "critical_strike_cold_steel.png": "SourceAssets/CriticalStrike20260914/critical_strike_cold_steel.png",
    "pistol_mastery_cold_steel.png": "SourceAssets/PistolMastery20260914/pistol_mastery_cold_steel.png",
    "rifle_mastery_cold_steel.png": "SourceAssets/Skills20260913/Candidates/rifle_mastery_B_M4_v2.png",
    "dexterous_hands.png": "SourceAssets/DexterousHands20260913/dexterous_hands.png",
    "dodge_cold_steel.png": "SourceAssets/DexterousHands20260913/dodge_cold_steel.png",
    "quick_combat_placeholder.png": "SourceAssets/QuickCombat20260917/quick_combat_placeholder.png",
}


def main():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for filename, source in ICONS.items():
        shutil.copy2(PROJECT / source, RUNTIME / filename)
        print(f"Restored {filename}")


if __name__ == "__main__":
    main()
