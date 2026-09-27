"""Durable catalog hook for the fixed entrance shrine; no layout generation."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def extend(catalog):
    catalog['start_shrine']=json.loads((ROOT/'Config/shrine.json').read_text(encoding='utf-8'))
    return catalog
