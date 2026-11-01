import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M24Repair20261027');(O/'UEExports').mkdir(exist_ok=True)
def tf(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return dict(p=[p.x,p.y,p.z],q=[q.x,q.y,q.z,q.w],s=[s.x,s.y,s.z])
def vec(p):return [p.x,p.y,p.z]
out={'assets':{},'actors':[],'textures':{},'world':None}
paths={'original':'/Game/Weapons/M24/Gameplay20261026/SK_M24_V9',
       'modular':'/Game/Weapons/M24/Modular20261027/SK_M24_ModularV9',
       'scope':'/Game/Weapons/M24/Modular20261027/SM_M24_m24_custom_scope_6x',
       'suppressor':'/Game/Weapons/M24/Modular20261027/SM_M24_m24_factory_suppressor'}
for key,path in paths.items():
    mesh=u.load_asset(path);row={'asset':mesh.get_path_name()}
    row['bounds']=str(mesh.get_bounds())
    row['import_data']=str(mesh.get_editor_property('asset_import_data'))
    if isinstance(mesh,u.SkeletalMesh):
        pose=u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
        row['reference']={n:tf(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in ('VM_Root','WPN_root','WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Magazine','hand_r')}
        row['materials']=[{'slot':str(v.material_slot_name),'asset':v.material_interface.get_path_name() if v.material_interface else None} for v in mesh.materials]
        row['build_settings']=str(u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_build_settings(mesh,0))
    else:
        row['materials']=[{'slot':str(v.material_slot_name),'asset':v.material_interface.get_path_name() if v.material_interface else None} for v in mesh.static_materials]
    out['assets'][key]=row
    (O/'ue_before.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    out['assets'][key]=row
for path in u.EditorAssetLibrary.list_assets('/Game/Weapons/M24/CustomScope20261026/Textures'):
    tex=u.load_asset(path)
    out['textures'][tex.get_name()]={k:str(tex.get_editor_property(k)) for k in ('srgb','compression_settings','flip_green_channel','asset_import_data')}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
out['world']=world.get_path_name() if world else None
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if 'FPSGAMECharacter' not in actor.get_class().get_name():continue
        row={'name':actor.get_name(),'parts':[]}
        for c in actor.get_components_by_class(u.MeshComponent):
            mesh=c.get_editor_property('skeletal_mesh_asset') if isinstance(c,u.SkeletalMeshComponent) else c.get_editor_property('static_mesh') if isinstance(c,u.StaticMeshComponent) else None
            if mesh and '/Weapons/M24/' in mesh.get_path_name():
                row['parts'].append({'component':c.get_name(),'mesh':mesh.get_path_name(),'transform':tf(c.get_world_transform()),'relative':tf(c.get_relative_transform()),'visible':c.is_visible()})
        if row['parts']:out['actors'].append(row)
(O/'ue_before.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'assets':list(out['assets']),'actors':out['actors'],'world':out['world']}))
