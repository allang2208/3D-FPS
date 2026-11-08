"""Restore the selected elemental Lightning Haste icon (legacy entry point)."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "SourceAssets/LightningHasteReview20261107/Icon/lightning_haste_cold_steel.png"
TARGET = ROOT / "Content/ColdSteelData/Skills/lightning_haste_cold_steel.png"

if __name__ == "__main__":
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, TARGET)
    print(f"Restored selected Lightning Haste icon: {TARGET}")
