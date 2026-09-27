import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent;S=P.parent
sources={
 'BowSurfaceRepair20260927/Bow_ElasticBodies_Outward.blend':['SK_Bow_Flex_'+r for r in ['Original','Swift','Heavy','Steady']],
 'BowGripContact20260927/Bow_GripContact.blend':['SM_Bow_GripWrap_Fitted'],
 'BowGripSeries20260927/Bow_GripSeries.blend':['SM_Bow_Grip_'+r for r in ['WovenLinen','SlimLeather','PaddedLeather']],
 'BowWoodBracket20260927/Bow_WoodBracketSight.blend':['SM_Bow_WoodBracketSight'],
 'BowModular20260926/Bow_ModularParts.blend':['SM_Bow_ArrowRestWood','SM_Bow_ArrowRestLined']}
rows=[]
for path,names in sources.items():
 bpy.ops.wm.open_mainfile(filepath=str(S/path))
 for name in names:
  o=bpy.data.objects[name]
  rows.append(dict(source=path,name=name,dimensions=list(o.dimensions),matrix=[list(r) for r in o.matrix_world],
    materials=[dict(name=m.name,nodes=[dict(type=n.type,image=(n.image.filepath if n.image else None)) for n in m.node_tree.nodes if n.type=='TEX_IMAGE']) for m in o.data.materials if m and m.use_nodes]))
(P/'source-inspection.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('BOW_ICON_SOURCES',json.dumps(rows))
