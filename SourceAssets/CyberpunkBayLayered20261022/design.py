"""Production coordinates: metres, +X screen-right, +Y across the bay, sea Z=0.
Apartment observation point=(0,0,91.7). UE conversion=(-X+10,+Y,Z-90)*100.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
DEST='/Game/Props/CyberpunkBayLayered20261022'
MAP='/Game/GameMaps/L_CyberpunkApartment'
OWNER='CyberpunkApartment.LayeredBay20261022'
SEED=221026
FACADES=ROOT/'Textures'
EXPORT=ROOT/'Meshes'
FAR_FACE_SIZE=4096
REFLECTION_FACE_SIZE=1024
EYE=(0,0,91.7)
WATER_PARENT='/Game/Clearwater/MI_ClearwaterWater'
SHARED={
 'Concrete':'/Game/Dungeons/ReceptionHall20261006/Materials/M_Reception_Stone',
 'Metal':'/Game/SubstrateMaterials/Materials/01_Paints/OpenPBR/MI_Paint_Black_SmallGrain_OPBR',
}
PALETTE=[(.055,.60,.85),(1.,.06,.26),(.85,.37,.10),(.31,.16,.75)]
