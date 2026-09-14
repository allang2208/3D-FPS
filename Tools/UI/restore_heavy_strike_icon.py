"""Restore only the selected heavy-strike icon from the local authoring image."""
from pathlib import Path
import shutil

PROJECT = Path(__file__).resolve().parents[2]

def main():
    source = PROJECT / "SourceAssets/HeavyStrike20260914/heavy_strike_cold_steel.png"
    target = PROJECT / "Content/ColdSteelData/Skills/heavy_strike_cold_steel.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    print("Restored heavy_strike_cold_steel.png")

if __name__ == "__main__":
    main()
