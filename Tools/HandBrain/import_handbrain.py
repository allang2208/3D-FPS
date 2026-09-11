import unreal,json,math
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');source=ROOT/'SourceAssets/HandBrain20260910/ue_export';dest='/Game/Monsters/HandBrain';report={}
tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.EditorAssetLibrary
def import_asset(path,name,options=None,folder=dest):
 if lib.does_asset_exist(folder+'/'+name):return unreal.load_asset(folder+'/'+name)
 t=unreal.AssetImportTask();t.filename=str(path);t.destination_path=folder;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True
 if options:t.options=options
 tools.import_asset_tasks([t]);a=unreal.load_asset(folder+'/'+name);assert a,(name,t.imported_object_paths)
 return a
opt=unreal.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
mesh=import_asset(source/'SK_HandBrain.fbx','SK_HandBrain',opt)
clips={}
for name,duration in [('Idle',2),('Move',1),('Attack_Slam',2),('Attack_Howl',3),('Death',2.8)]:
 opt=unreal.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;opt.skeleton=mesh.skeleton
 opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False
 opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
 a=import_asset(source/('A_HandBrain_'+name+'.fbx'),'A_HandBrain_'+name,opt);assert abs(a.get_play_length()-duration)<.04,(name,a.get_play_length());clips[name]=a
 a.set_editor_property('enable_root_motion',False);a.set_preview_skeletal_mesh(mesh);lib.save_loaded_asset(a)
report['clips']={k:{'path':v.get_path_name(),'seconds':v.get_play_length()} for k,v in clips.items()}
mf=ROOT/'SourceAssets/HandBrain20260910/howl_rebuild_v02/delivery';defs=json.loads((mf/'ue_materials.json').read_text());by_name={d['material']:d for rows in defs.values() for d in rows}
names=json.loads((source/'material_slots.json').read_text());mel=unreal.MaterialEditingLibrary
def material(name):
 p=dest+'/Materials/'+name
 if lib.does_asset_exist(p):m=unreal.load_asset(p);mel.delete_all_material_expressions(m)
 else:m=tools.create_asset(name,dest+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
 return m
made=[]
for i,name in enumerate(names):
 d=by_name[name];m=material('M_HandBrain_'+str(i));m.set_editor_property('two_sided',False)
 for sem,prop in [('BaseColor',unreal.MaterialProperty.MP_BASE_COLOR),('Normal_DirectX',unreal.MaterialProperty.MP_NORMAL),('Roughness',unreal.MaterialProperty.MP_ROUGHNESS)]:
  if sem not in d:continue
  val=d[sem]
  if isinstance(val,dict):
   tex=import_asset(mf/val['file'],'T_'+str(i)+'_'+sem,folder=dest+'/Textures');tex.set_editor_property('srgb',val['sRGB'])
   if sem=='Normal_DirectX':tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
   lib.save_loaded_asset(tex)
   n=mel.create_material_expression(m,unreal.MaterialExpressionTextureSample);n.texture=tex
   if sem=='Normal_DirectX':n.sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
   elif sem=='Roughness':n.sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
   mel.connect_material_property(n,'R' if sem=='Roughness' else 'RGB',prop)
  elif isinstance(val,list):
   n=mel.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);n.constant=unreal.LinearColor(*val);mel.connect_material_property(n,'',prop)
  else:
   n=mel.create_material_expression(m,unreal.MaterialExpressionConstant);n.r=float(val);mel.connect_material_property(n,'',prop)
 mel.recompile_material(m);lib.save_loaded_asset(m);made.append(m)
slots=mesh.get_editor_property('materials');assert len(slots)==len(made),(len(slots),len(made))
for i,slot in enumerate(slots):slot.material_interface=made[i];slots[i]=slot
mesh.set_editor_property('materials',slots)
pa_path=dest+'/PA_HandBrain'
pa=unreal.HandBrainMonster.create_physics_asset(mesh)
assert unreal.HandBrainMonster.build_physics_asset(mesh,pa);lib.save_loaded_asset(pa);lib.save_loaded_asset(mesh)
# Read the actual imported reference-bone axis rather than guessing FBX orientation.
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);temp=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector())
comp=temp.skeletal_mesh_component;comp.set_skeletal_mesh_asset(mesh);a=comp.get_socket_location('crown_00');b=comp.get_socket_location('cranium');yaw=-math.degrees(math.atan2(a.y-b.y,a.x-b.x));actors.destroy_actor(temp)
# Thin, unlit ground ring: exact gameplay radius, no collision or shadows.
ring=material('M_HandBrain_GroundRing');ring.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT);ring.set_editor_property('two_sided',True);ring.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
uv=mel.create_material_expression(ring,unreal.MaterialExpressionTextureCoordinate)
center=mel.create_material_expression(ring,unreal.MaterialExpressionConstant2Vector);center.r=.5;center.g=.5
outer=mel.create_material_expression(ring,unreal.MaterialExpressionSphereMask);inner=mel.create_material_expression(ring,unreal.MaterialExpressionSphereMask)
for n,r in [(outer,.49),(inner,.465)]:
 n.set_editor_property('attenuation_radius',r);n.set_editor_property('hardness_percent',95);mel.connect_material_expressions(uv,'',n,'A');mel.connect_material_expressions(center,'',n,'B')
sub=mel.create_material_expression(ring,unreal.MaterialExpressionSubtract);mel.connect_material_expressions(outer,'',sub,'A');mel.connect_material_expressions(inner,'',sub,'B')
opacity=mel.create_material_expression(ring,unreal.MaterialExpressionScalarParameter);opacity.set_editor_property('parameter_name','Opacity');opacity.set_editor_property('default_value',1.0)
mul=mel.create_material_expression(ring,unreal.MaterialExpressionMultiply);mel.connect_material_expressions(sub,'',mul,'A');mel.connect_material_expressions(opacity,'',mul,'B');mel.connect_material_property(mul,'',unreal.MaterialProperty.MP_OPACITY)
tint=mel.create_material_expression(ring,unreal.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','Tint');tint.set_editor_property('default_value',unreal.LinearColor(1,.1,.02,1));mel.connect_material_property(tint,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR);mel.recompile_material(ring);lib.save_loaded_asset(ring)
sounds={k:import_asset(source/(k+'.wav'),'S_HandBrain_'+k,folder=dest+'/Audio') for k in ['slam','howl','move']}
bp_path=dest+'/BP_HandBrain'
if lib.does_asset_exist(bp_path):bp=unreal.load_asset(bp_path)
else:
 factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.HandBrainMonster);bp=tools.create_asset('BP_HandBrain',dest,unreal.Blueprint,factory)
unreal.BlueprintEditorLibrary.compile_blueprint(bp);cdo=unreal.get_default_object(bp.generated_class());cdo.set_editor_property('visual_mesh',mesh);cdo.mesh.set_skeletal_mesh_asset(mesh)
cdo.mesh.set_relative_rotation(unreal.Rotator(pitch=0,yaw=yaw,roll=0),False,False)
for prop,key in [('idle_clip','Idle'),('move_clip','Move'),('slam_clip','Attack_Slam'),('howl_clip','Attack_Howl'),('death_clip','Death')]:cdo.set_editor_property(prop,clips[key])
for k,v in sounds.items():cdo.set_editor_property(k+'_sound',v)
cdo.set_editor_property('ground_ring_material',ring);lib.save_loaded_asset(bp,False)
report.update({'mesh':mesh.get_path_name(),'physics':pa.get_path_name(),'blueprint':bp_path,'mesh_yaw':yaw,'material_slots':[str(s.material_slot_name) for s in slots]})
(ROOT/'Saved/HandBrain/import.json').write_text(json.dumps(report,indent=2));unreal.log('HANDBRAIN_IMPORT_COMPLETE '+json.dumps(report))
