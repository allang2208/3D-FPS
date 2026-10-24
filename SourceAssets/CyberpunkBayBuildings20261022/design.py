from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
OLD=PROJECT/'SourceAssets/CyberpunkBayLayered20261022'
DEST='/Game/Props/CyberpunkBayBuildings20261022'
MAP='/Game/GameMaps/L_CyberpunkApartment'
OWNER='CyberpunkApartment.DetailedBay20261022'
EXPORT=ROOT/'Meshes'
FACADES=ROOT/'Textures'
FAR_FACE_SIZE=4096
REFLECTION_FACE_SIZE=2048
EYE=(0,0,91.7)
FLOOR=3.8
ATLAS_METRES=(76.8,121.6)
PALETTE=[(.055,.60,.85),(1.,.06,.26),(.85,.37,.10),(.31,.16,.75)]
