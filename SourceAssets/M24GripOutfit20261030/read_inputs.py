from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O.parent/'M24IdleArm20261030/read_inputs.py').read_text(),'read_current','exec'))
exec(compile((O.parent/'M24IdleArm20261030/read_roles.py').read_text(),'read_roles','exec'))
config=json.loads((O.parents[1]/'Content/ColdSteelData/modular_outfits.json').read_text());path=mesh.get_path_name();profile=config['profiles'][path]
paths={'M24':path,'M4': '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416','base':profile['native_bare_skin']}
for key,item in config['items'].items():
    if item.get('slot') in (3,7) and item.get('rig_meshes',{}).get('M4'):paths[key]=item['rig_meshes']['M4']
out={}
for label,p in paths.items():
    asset=u.load_asset(p)
    if not asset:out[label]={'path':p,'exists':False};continue
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    out[label]={'path':p,'exists':True,'skeleton':asset.skeleton.get_path_name(),'materials':[str(m.material_slot_name) for m in asset.materials],
        'bones':{str(b.name):{'parent':b.parent_index,'index':b.index,'local':tr(b.local_transform),'world':tr(b.world_transform)} for b in bones}}
(O/'equipment_inputs.json').write_text(json.dumps(out));(O/'outfit_profile_before.json').write_text(json.dumps(profile,indent=2))
runtime=[]
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if 'FPSGAMECharacter' not in actor.get_class().get_name():continue
    runtime.append({'actor':actor.get_path_name(),'components':[{'name':c.get_name(),'mesh':c.get_skinned_asset().get_path_name() if c.get_skinned_asset() else '', 'visible':c.is_visible(),'scale':str(c.get_relative_scale3d()),'tags':[str(x) for x in c.component_tags]} for c in actor.get_components_by_class(u.SkeletalMeshComponent)]})
(O/'runtime_sources.json').write_text(json.dumps(runtime));print('M24_EQUIPMENT_INPUTS',len(out),len(runtime),flush=True)
