"""Import the reference-shaped R5 groom, reusing the current female native hair effect."""
from pathlib import Path
import hashlib
base=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/save_assets.py').read_text(encoding='utf-8-sig')
exec(compile(base.split('E.make_directory(DEST)')[0],'<nun helpers>','exec'))
R=P/'SourceAssets/ChapelNun20261115/HairReferenceR5';O=R/'Authored';DEST='/Game/Characters/ChapelNun20261115/HairReferenceR5';E.make_directory(DEST)
receipt_path=R/'saved_assets.json';receipt=read(receipt_path) if receipt_path.exists() else {'assets':{},'completed':False}
head=load('/Game/Characters/ChapelNun20261115/RefinementR4/Meshes/SK_Nun_OriginalMeshyFace_Final')
native=load('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Grooms/MI_WI_Hair_L_Straight_Hair')
mat=load(DEST+'/Materials/MI_Nun_Hair')
# User accepted the existing shading: reuse the material without modifying it.
reference=load('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Grooms/Hair_L_Straight')
grooms=[]
for name,simulate in [('Nun_LowBun_Core_R5',False),('Nun_LowBun_Loose_R5',True)]:
 digest=hashlib.sha256((O/(name+'.abc')).read_bytes()).hexdigest()
 path=DEST+'/Grooms/'+name
 asset=u.load_asset(path)
 if asset and receipt.get('source_hashes',{}).get(name)!=digest:
  raise RuntimeError('Changed groom requires offline package replacement: '+path)
 if not asset:
  task=u.AssetImportTask();task.filename=str(O/(name+'.abc'));task.destination_path=DEST+'/Grooms';task.destination_name=name;task.automated=True;task.save=False;task.replace_existing=False;task.factory=u.HairStrandsFactory()
  options=u.GroomImportOptions();conversion=options.get_editor_property('conversion_settings');conversion.set_editor_property('rotation',u.Vector(-90,0,0));conversion.set_editor_property('scale',u.Vector(1,1,1));options.set_editor_property('conversion_settings',conversion);task.options=options;A.import_asset_tasks([task])
  asset=load(path)
 receipt.setdefault('source_hashes',{})[name]=digest
 asset.set_editor_property('enable_global_interpolation',False)
 physics=reference.get_editor_property('hair_groups_physics')[0];solver=physics.get_editor_property('solver_settings');solver.set_editor_property('enable_simulation',simulate);solver.set_editor_property('sub_steps',6);solver.set_editor_property('iteration_count',8);physics.set_editor_property('solver_settings',solver)
 forces=physics.get_editor_property('external_forces');forces.set_editor_property('air_drag',.65);physics.set_editor_property('external_forces',forces)
 constraints=physics.get_editor_property('material_constraints');collision=constraints.get_editor_property('collision_constraint');collision.set_editor_property('collision_radius',.18);constraints.set_editor_property('collision_constraint',collision)
 bend=constraints.get_editor_property('bend_constraint');bend.set_editor_property('bend_stiffness',.22);bend.set_editor_property('bend_damping',.12);constraints.set_editor_property('bend_constraint',bend);physics.set_editor_property('material_constraints',constraints);asset.set_editor_property('hair_groups_physics',[physics])
 slots=list(reference.get_editor_property('hair_groups_materials'))
 for slot in slots:slot.set_editor_property('material',mat)
 asset.set_editor_property('hair_groups_materials',slots)
 render=reference.get_editor_property('hair_groups_rendering')[0];geom=render.get_editor_property('geometry_settings');geom.set_editor_property('hair_width',.0068 if not simulate else .0048);geom.set_editor_property('hair_tip_scale',.08);render.set_editor_property('geometry_settings',geom);asset.set_editor_property('hair_groups_rendering',[render])
 group=asset.get_editor_property('hair_groups_lod')[0];group.import_text('(LODs=((ScreenSize=1.0,GeometryType=Strands),(CurveDecimation=0.65,VertexDecimation=0.75,ScreenSize=0.15,ThicknessScale=1.15,GeometryType=Strands),(CurveDecimation=0.30,VertexDecimation=0.55,ScreenSize=0.045,ThicknessScale=1.45,GeometryType=Strands,Simulation=Disable)))');asset.set_editor_property('hair_groups_lod',[group]);save(asset);grooms.append((name,asset))
if not u.ChapelNunQualityCommandlet.apply_refined_root_uv():raise RuntimeError('Native root UV assignment failed')
# Finalize groom data before creating any binding: rebuilding the groom while a
# previous binding compiles can invalidate the HairStrands worker's input buffers.
for name,asset in grooms:save(asset)
for name,asset in grooms:
 binding=u.load_asset(DEST+'/Grooms/'+name+'_Binding')
 if not binding:binding=u.GroomLibrary.create_new_groom_binding_asset_with_path(DEST+'/Grooms/'+name+'_Binding',asset,head,100,None,0)
 save(binding);receipt['assets'][name]=asset.get_path_name();receipt['assets'][name+'_Binding']=binding.get_path_name();record()
receipt.update(completed=True,head=head.get_path_name(),material=mat.get_path_name(),native_hair_material=native.get_path_name(),authoring=read(R/'authoring.json'),runtime_tested=False)
record();print('REFERENCE_HAIR_SAVED',flush=True)
