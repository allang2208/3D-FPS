from pathlib import Path
import runpy
R=Path(__file__).resolve().parent;PROJECT=R.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV17';MAP='/Game/GameMaps/L_CyberpunkApartment'
FAMILIES=['WarmBands','PearlVertical','AmberTerrace','BlueFrame','CopperArcade','QuietGlass']
SOURCE_FAMILY=dict(WarmBands='Financial',PearlVertical='Corporate',AmberTerrace='Terraces',BlueFrame='Data',CopperArcade='Harbor',QuietGlass='Housing')
PALETTE=dict(WarmBands=(1.,.66,.30),PearlVertical=(.64,.80,1.),AmberTerrace=(1.,.48,.18),BlueFrame=(.10,.31,1.),CopperArcade=(1.,.64,.32),QuietGlass=(.45,.62,.78))
LIGHTS=dict(Gold=(1.,.63,.28),Pearl=(.65,.82,1.),Blue=(.055,.24,1.),Amber=(1.,.36,.10),Teal=(.04,.48,.54))
SHIFT=-615.
