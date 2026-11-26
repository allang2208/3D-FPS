"""Generate the revision-specific GAME sources and standard inventory-art producers."""
from pathlib import Path
T=Path('D:/FPS3D/FPSGAME/Tools/ModernTacticalSet')
for name in ['sources','lower_sources']:
    s=(T/f'combat2_{name}.py').read_text(encoding='utf-8').replace('CombatShirtR2','CombatShirtR3').replace('TS01_R2','TS01_R3').replace("bs.inputs['Sheen Weight'].default_value=.14","bs.inputs['Sheen Weight'].default_value=.38")
    needle="tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT'"
    s=s.replace(needle,needle+";coords=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=8/28.8;links.new(coords.outputs['UV'],scale.inputs[0]);links.new(scale.outputs['Vector'],tex.inputs['Vector'])")
    s=s.replace("u,v=uv.data[li].uv;offsets", "u,v=uv.data[li].uv;u*=8/28.8;v=1-(1-v)*8/28.8;offsets")
    if name=='sources':
        s=s.replace("if m in ['TS01_RangerRipstop','TS01_RangerNylon']:vest['materials'][i]='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3/Materials/M_'+('CombatRipstop' if m=='TS01_RangerRipstop' else 'CombatCarrier')", "if m in ['TS01_RangerRipstop','TS01_RangerNylon','TS01_OliveWebbing','TS01_CharcoalStretch','TS01_StitchThread']:vest['materials'][i]='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3/Materials/M_'+({'TS01_RangerRipstop':'CombatRipstop','TS01_CharcoalStretch':'CombatStretch','TS01_StitchThread':'CombatThread'}.get(m,'CombatCarrier'))")
    (T/f'combat3_{name}.py').write_text(s,encoding='utf-8')
print('TS01_R3_ART_PRODUCERS_READY')
