"""Fine connected lightning inlay, preserving the corrected V2 crown and body UVs."""
import bpy,bmesh,ast,types,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent;ROOT=P.parents[2];V1=P.parent/'StormDriveBuildV1';V2=P.parent/'StormDriveTrimV2'
RUNE=ROOT/'SourceAssets/RuneboundWarhammer20261022'
code=(RUNE/'FinalTollHammerHeadV2/author_model.py').read_text('utf-8')
m=types.ModuleType('rune_tools');m.__file__=str(P/'repair_rune.py');exec(compile(code,'<solid_tools>','exec'),m.__dict__)
tree=ast.parse((V2/'repair_model.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('key','extract_preserved')],type_ignores=[]),'<preserve_original_uv>','exec'))
removals={};reports=[]
for label in ('Steel','Runebound'):
    bpy.ops.wm.open_mainfile(filepath=str(V1/('StormDrive_'+label+'_Construction.blend')))
    deps=bpy.context.evaluated_depsgraph_get();remove=set();count=0
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or obj.get('host_variant')!=label or not obj.name.startswith('Solid_vertical_resonance_plate'):continue
        evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh();remove.update(key(obj.matrix_world@v.co) for v in mesh.vertices)
        evaluated.to_mesh_clear();count+=1
    assert count==2,(label,count)
    removals[label]=remove
bpy.ops.wm.open_mainfile(filepath=str(V2/'StormDriveSeats_Editable_V2.blend'))
models={}
for label in ('Steel','Runebound'):
    old=bpy.data.objects['SM_'+label+'Warhammer_StormDrive_V2'];mesh=old.data;remove=removals[label]
    coordinates={key(v.co) for v in mesh.vertices}
    assert len(remove&coordinates)==len(remove),(label,len(remove),len(remove&coordinates))
    glow_slots={i for i,mat in enumerate(mesh.materials) if mat.name.startswith('M_StormDrive_GoldInlay')}
    remove.update(key(mesh.vertices[v].co) for p in mesh.polygons if p.material_index in glow_slots for v in p.vertices)
    new,record=extract_preserved(old,'SM_'+label+'Warhammer_StormDrive_V3',remove)
    record['variant']=label;reports.append(record);models[label]=new
    bpy.data.objects.remove(old,do_unlink=True);new.hide_set(True);new.hide_render=True

bpy.context.preferences.view.use_translate_new_dataname=False;bpy.context.preferences.view.use_translate_interface=False
m.PARTS=[];m.ENERGY=[];m.BUILD=bpy.data.collections.new('03_Fine_Lightning_Master');bpy.context.scene.collection.children.link(m.BUILD)
tree=ast.parse((V1/'author_model.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('arch','ring')],type_ignores=[]),'<retained_plate_outline>','exec'))
sys.path.insert(0,str(RUNE/'HeadRunePBRV3'));from surface_authoring import refine_metal
bronze=m.procedural_metal('AUTHOR_RunePlate_BrushedBronze',(.13,.083,.033),(.29,.19,.074),.38,.000018)
gold=m.procedural_metal('AUTHOR_RuneInlay_PolishedGold',(.37,.23,.073),(.59,.41,.17),.24,.000009)
for material in (bronze,gold):refine_metal(material)
energy=bpy.data.materials['M_StormDrive_GoldInlay']
f=m.frame((0,-.0255,.931),(0,-1,0),(1,0,0));w=.0385;h=.054
shapes=json.loads((P/'rune_footprints.json').read_text('utf-8'))
def freeze(obj):
    m.activate(obj)
    for modifier in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=modifier.name)
def carve(obj,shape,d0,d1,label):
    tool=m.strip(label,f,shape,d0,d1,bronze,0,[]);freeze(obj);m.activate(obj)
    mod=obj.modifiers.new(label,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True)
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    bevel=obj.modifiers.new('Fine chisel edge radius','BEVEL');bevel.width=.000025;bevel.segments=3;bevel.limit_method='ANGLE';bevel.use_clamp_overlap=True
    obj.modifiers.new('Preserved broad face normals','WEIGHTED_NORMAL').keep_sharp=True
plate=m.strip('Refined_solid_resonance_plate',f,arch(w*.29,h*.72),.0007,.0045,bronze,.00025)
carve(plate,shapes['channel'],.00377,.0050,'True_continuous_lightning_groove')
inlay=m.strip('Tapered_polished_gold_lightning',f,shapes['metal'],.00380,.00435,gold,.000035)
carve(inlay,shapes['light'],.00415,.0046,'Fine_recessed_luminous_core')
glow=m.strip('Seated_fine_luminous_core',f,shapes['light'],.00414,.00427,energy,.000008,m.ENERGY)
ring('Fine_closed_plate_border',f,arch(w*.278,h*.704),arch(w*.262,h*.687),.00436,.00464,gold)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StormDrive_Rune_Construction.blend'))
metal=m.join_group(m.PARTS,'FineRune_Metal_Master');m.unwrap(metal)
start=code.index('def bake_maps(');end=code.index('\ndef finalize(',start)
bake=code[start:end].replace('4096','2048').replace('T_FinalToll_','T_StormDrive_RunePlate_').replace('M_FinalToll_PBR_Surface','M_StormDrive_RunePlate_V3')
exec(compile(bake,'<rune_plate_pbr>','exec'),m.__dict__);m.bake_maps(metal)
glow=m.join_group(m.ENERGY,'FineRune_Luminous_Master');m.unwrap(glow)
master=m.join_group([metal,glow],'FineRune_Front_Master')
bm=bmesh.new();bm.from_mesh(master.data);boundary=sum(e.is_boundary for e in bm.edges);bm.free()
assert boundary==0,boundary
def duplicate(label,back=False):
    obj=master.copy();obj.data=master.data.copy();bpy.context.scene.collection.objects.link(obj)
    sx=(.0335/.0385) if label=='Runebound' else 1.;sz=(.063/.054) if label=='Runebound' else 1.;cx=-.0004452141 if label=='Runebound' else 0.;cz=.917 if label=='Runebound' else .931
    sign=-1 if back else 1;normal_matrix=Matrix.Diagonal((sign/sx,sign,1/sz));normals=[n.vector.copy() for n in obj.data.corner_normals]
    for v in obj.data.vertices:
        v.co.x=sign*v.co.x*sx+cx;v.co.y=sign*(v.co.y+(.0015 if label=='Runebound' else 0));v.co.z=(v.co.z-.931)*sz+cz
    obj.data.normals_split_custom_set([(normal_matrix@n).normalized() for n in normals]);return obj
rows=[]
for label in ('Steel','Runebound'):
    pieces=[duplicate(label,back) for back in (False,True)];base=models[label];base.hide_set(False);base.hide_render=False
    model=m.join_group([base]+pieces,base.name);model['model_revision']='StormDriveRuneV3'
    model.data.calc_loop_triangles();m.activate(model);fbx=P/'Export'/(model.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
    rows.append({'variant':label,'mesh':model.name,'fbx':str(fbx),'triangles':len(model.data.loop_triangles),'materials':[mat.name for mat in model.data.materials]})
    models[label]=model;model.hide_set(True);model.hide_render=True
bpy.data.objects.remove(master,do_unlink=True);models['Steel'].hide_render=False;models['Steel'].hide_set(False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StormDriveSeats_Editable_V3.blend'))
(P/'repair_receipt.json').write_text(json.dumps({'complete':True,'parts':rows,'preservation':reports,'rune_boundary_edges':boundary,'crown_v2_retained':True,'game_tested':False},indent=2),encoding='utf-8')
print('STORM_DRIVE_FINE_RUNE_V3_EXPORTED',flush=True)
