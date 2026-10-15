import bpy, json
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
out={}
for label,path in [('bare','SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/Pickaxe_BareArmsV7.blend'),('pickaxe','SourceAssets/RusticPickaxe20260919/RusticPickaxe_TwoHand_Editable.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/path))
    rows=[]
    for o in bpy.context.scene.objects:
        if o.type not in ('MESH','ARMATURE'):continue
        row={'name':o.name,'type':o.type,'matrix_world':[list(r) for r in o.matrix_world]}
        if o.type=='MESH':row.update(vertices=len(o.data.vertices),materials=[m.name if m else '' for m in o.data.materials],groups=[g.name for g in o.vertex_groups][:8])
        else:row.update(bones=len(o.data.bones),wpn_rest=[list(r) for r in o.data.bones['WPN_root'].matrix_local] if 'WPN_root' in o.data.bones else None)
        rows.append(row)
    out[label]={'objects':rows,'actions':[a.name for a in bpy.data.actions]}
(P/'authoring_inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
