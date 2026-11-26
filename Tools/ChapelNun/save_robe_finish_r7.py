"""Nun-only woven wool finish and plain collar; preserve robe cloth data."""
from pathlib import Path
base=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/save_assets.py').read_text(encoding='utf-8-sig')
helpers=base.split('E.make_directory(DEST)')[0]
helpers=helpers.replace('(.018,.017,.016)', '(.036,.033,.030)')
helpers=helpers.replace('wire(norm,attrs,\'Normal\',\'RGB\')', """normal_detail=node(mat,u.MaterialExpressionCustom,code='float2 p=UV*96.; float2 width=max(fwidth(p),float2(.001,.001)); float2 fade=1-smoothstep(.12,.65,width); float2 weave=float2(sin(p.x*6.283185),sin(p.y*6.283185))*fade*.035; return normalize(float3(N.xy*.65+weave,N.z));',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
 normal_detail.set_editor_property('inputs',[pin('UV'),pin('N')]);wire(cu,normal_detail,'UV');wire(norm,normal_detail,'N','RGB');wire(normal_detail,attrs,'Normal')""")
helpers=helpers.replace("wire(constant(mat,.90 if lining else .84),attrs,'Roughness')", """rough=node(mat,u.MaterialExpressionCustom,code='return clamp(.79+Mask*.11+.018*sin(UV.x*2.7)*sin(UV.y*3.9),.79,.94);',output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
 rough.set_editor_property('inputs',[pin('UV'),pin('Mask')]);wire(cu,rough,'UV');wire(orm,rough,'Mask','G');wire(rough,attrs,'Roughness')""")
exec(compile(helpers,'<nun finish helpers>','exec'))
black=cloth('M_Nun_WovenWool_R7');skirt=cloth('M_Nun_WovenSkirt_R7',skirt=True)
lining=cloth('M_Nun_WovenLining_R7',lining=True);ivory=cloth('M_Nun_LinenCollar_R7',ivory=True)
robe=load(DEST+'/Meshes/SK_Nun_BlackRobe');cloth_count=len(robe.mesh_clothing_assets)
slots=list(robe.materials)
for slot in slots:
 label=str(slot.material_slot_name)
 if label not in ('RobeSilver','RobeGem'):
  slot.material_interface=skirt if label=='RobeSkirt' else lining if label in ('SleeveLining','TorsoLining','RobeSimulationProxy') else black
robe.set_editor_property('materials',slots);save(robe)
# Use the latest neck-clearance source, retaining its shape, skinning and UVs.
source_file=P/'SourceAssets/ChapelNun20261115/IdleBackReviewR2/Authored/trim.json'
d=read(source_file);keep=[i for i,m in enumerate(d['triangle_materials']) if m==0]
if not keep or len(keep)==len(d['triangles']):raise RuntimeError('Expected collar plus removable pendant surfaces')
for key in ('triangles','normals','uv','triangle_materials'):d[key]=[d[key][i] for i in keep]
d['material_slots']=d['material_slots'][:1]
R=P/'SourceAssets/ChapelNun20261115/IdleCrossedR7';O=R/'Authored';O.mkdir(exist_ok=True)
(O/'plain_collar.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
receipt_path=R/'robe_finish_saved.json';receipt={'completed':False,'assets':{},'runtime_tested':False}
trim=skeletal('plain_collar.json','SK_Nun_PlainCollar_R7',[ivory])
ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
build=ss.get_lod_build_settings(trim,0);build.set_editor_property('use_full_precision_u_vs',True);ss.set_lod_build_settings(trim,0,build)
ss.regenerate_lod(trim,3,True,False);save(trim)
receipt.update(completed=True,robe=robe.get_path_name(),materials=[x.get_path_name() for x in (black,skirt,lining,ivory)],cloth_assets_preserved=cloth_count,removed_pendant_triangles=len(read(source_file)['triangles'])-len(keep),collar_triangles=len(keep))
record();print('NUN_ROBE_FINISH_R7_SAVED',json.dumps(receipt),flush=True)
