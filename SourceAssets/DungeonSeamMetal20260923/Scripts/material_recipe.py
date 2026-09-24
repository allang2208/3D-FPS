"""Scoped replacement families; existing paint identities remain distinct."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='/Game/Dungeons/SeamMetal20260923'
ROWS=[]
def add(folder,name,tint,metal,rough,rust,tile=100,channel=(1,0,0),edge=(0,1,0)):
    ROWS.append(dict(old=folder+'/M_'+name,name='MI_'+name,tint=tint,metal=metal,rough=rough,rust=rust,tile=tile,channel=channel,edge=edge))
at='/Game/Dungeons/AtmosphereV2/Materials'
add(at,'PaintedSteel',(.13,.17,.125),.04,.53,.30)
add(at,'BareSteel',(.24,.265,.27),.92,.39,.23,80,edge=(0,0,0))
add('/Game/Dungeons/AtmosphereV2/Services/Materials','Service_Paint',(.17,.205,.145),.03,.55,.36,90,edge=(0,0,0))
combat='/Game/Dungeons/CombatExpansion20260922/Materials'
add(combat,'PipeEnamel',(.17,.205,.145),.03,.50,.32,90,edge=(0,0,0))
add(combat,'PipeCutSteel',(.28,.295,.29),.94,.34,.16,80,edge=(0,0,0))
add(combat,'PipeInner',(.085,.075,.060),.45,.74,.48,80,edge=(0,0,0))
add(combat,'BridgeDeck',(.16,.18,.17),.86,.53,.36)
boss='/Game/Dungeons/BossHall20260922/Materials'
add(boss,'BossMachinePaint',(.19,.235,.175),.04,.50,.32,120)
add(boss,'BossStructuralSteel',(.11,.145,.13),.12,.52,.36,110)
add(boss,'BossGrating',(.205,.22,.215),.90,.49,.33,100,edge=(0,0,0))
add(boss,'BossPipeCoat',(.19,.225,.165),.03,.49,.28,90,channel=(0,1,0),edge=(0,0,0))
add(boss,'BossPipeHardware',(.25,.27,.265),.93,.38,.24,80,channel=(0,1,0),edge=(0,0,0))
interior='/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials'
add(interior,'Room_Iron',(.15,.17,.17),.89,.53,.38)
add(interior,'Room_Rust',(.16,.14,.11),.65,.68,.95,110,edge=(0,0,0))
add(interior,'Room_GreenPaint',(.13,.20,.135),.03,.54,.31)
add(interior,'Room_RedPaint',(.25,.048,.026),.03,.55,.27)
add(interior,'Room_YellowPaint',(.50,.31,.055),.03,.56,.18)
freight='/Game/Dungeons/FreightDoor20260923/Materials'
add(freight,'FreightCoat',(.13,.17,.125),.04,.52,.20,100,channel=(0,0,1))
add(freight,'FreightTrack',(.28,.30,.29),.92,.33,.12,80,channel=(0,0,1))
add(freight,'FreightGate',(.095,.12,.10),.46,.49,.24,100,channel=(0,0,1))
add(freight,'FreightPanel',(.32,.34,.275),.03,.48,.10,100,channel=(0,0,1))

def remap():return {r['old']:BASE+'/Materials/'+r['name'] for r in ROWS}
