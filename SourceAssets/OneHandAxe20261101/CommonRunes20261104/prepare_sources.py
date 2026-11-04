"""Freeze current head sources and reuse the three shared one-handed rune definitions."""
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent;AXE=P.parent;PROJECT=P.parents[2]
DATA=PROJECT/'Content/ColdSteelData'
for name in ['Before','Textures','Editable']:(P/name).mkdir(parents=True,exist_ok=True)
catalog=json.loads((DATA/'tactical-hatchet-modules.json').read_text('utf-8'))
r5=AXE/'BladeVariants20261102/ContinuousBladesR5_20261104'
r4=AXE/'BladeVariants20261102/CrescentReferenceR4_20261104'
specs=[
 ('factory','Factory',AXE/'ModulesV1/TacticalHatchet_Modules_Editable.blend','SM_TacticalHatchet_Head_Factory',AXE/'Textures/source_image_01.png'),
 ('axe_swift_crescent','SwiftCrescent',r4/'SwiftCrescent_Editable.blend','SM_TacticalHatchet_Head_SwiftCrescent_R4',r4/'FactoryFinish20261104/Textures/T_TacticalHatchet_Head_SwiftCrescent_R4_BaseColor.png'),
 ('axe_heavy_cleaver','HeavyCleaver',r5/'HeavyCleaver_Editable.blend','SM_TacticalHatchet_Head_HeavyCleaver_R5',r5/'HeavyCleaver/Textures/T_TacticalHatchet_Head_HeavyCleaver_R5_BaseColor.png'),
 ('axe_folded_arc','FoldedArc',r5/'FoldedArc_Editable.blend','SM_TacticalHatchet_Head_FoldedArc_R5',r5/'FoldedArc/Textures/T_TacticalHatchet_Head_FoldedArc_R5_BaseColor.png'),
 ('hatchet_falcon_edge','FalconEdge',AXE/'FalconEdge20261103/TacticalHatchet_FalconEdge_Editable.blend','SM_TacticalHatchet_Head_FalconEdge',AXE/'FalconEdge20261103/Textures/T_TacticalHatchet_Head_FalconEdge_BaseColor.png')]
entries=[]
for id,kind,blend,obj,base in specs:
    spec=catalog['slots']['blade_1'][id]
    slot=spec['material_slot_names'][0]
    entries.append(dict(id=id,kind=kind,blend=str(blend),object=obj,basecolor_file=str(base),mesh=spec.get('rune_carrier_source_mesh',spec['mesh']),
        slot=slot,material=spec['materials'][slot],target_slot='M_TacticalHatchet_Head_Factory_RuneCarrier' if id=='factory' else slot))
shared=json.loads((DATA/'shared-knife-component-options.json').read_text('utf-8'))
runes=next(c['options'] for c in shared['columns'] if c['key']=='blade_2')
kinds={'knife_mark_wing':'RuneWing','knife_mark_knot':'RuneKnot','knife_mark_peaks':'RunePeaks'}
tints={'knife_mark_wing':[.42,.27,.09,1],'knife_mark_knot':[.60,.62,.64,1],'knife_mark_peaks':[.035,.04,.045,1]}
for entry in runes:
    entry['kind']=kinds[entry['id']]
    entry['tint']=tints[entry['id']]
    entry['glyph']=str(PROJECT/'SourceAssets/KukriComponentVariants20261026/Concepts'/(entry['id']+'.png'))
    entry['icon_key']='blade_2_'+entry['id']
(P/'sources.json').write_text(json.dumps({'heads':entries,'runes':runes},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('HATCHET_RUNE_SOURCES heads=5 shared_runes=3')
