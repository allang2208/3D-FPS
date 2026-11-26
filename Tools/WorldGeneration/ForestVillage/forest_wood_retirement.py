"""Shared with the editor's legacy point-stream reader."""
from pathlib import Path

CATALOG=Path(__file__).resolve().parents[3]/'Config/ForestVillageRetiredWood.txt'

def retired_meshes():
    return frozenset(CATALOG.read_text(encoding='utf-8-sig').splitlines())

def active_points(records,palette):
    """Drop retired rows and compact only extended slots, keeping surviving transforms and order."""
    import numpy as np
    retired=retired_meshes()
    keep=np.array([True]*16+[p not in retired for p in palette],dtype=bool)
    slots=records['slot']
    if len(slots) and (slots.min()<0 or slots.max()>=len(keep)):
        raise ValueError('Forest point outside its source palette')
    if keep.all():return records,palette
    result=records[keep[slots]].copy()
    result['slot']=(keep.cumsum()-1)[result['slot']]
    return result,[p for p in palette if p not in retired]
