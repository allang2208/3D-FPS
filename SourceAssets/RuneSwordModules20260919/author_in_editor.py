"""Split the current sword with Vibe3D in the open editor, preserving source assets.

This authors assets and exports editable geometry; it does not run a game or render.
"""
import unreal as u,json
from pathlib import Path
P=Path(__file__).parent; OUT=P/'Export'; OUT.mkdir(exist_ok=True)
D='/Game/Weapons/AzureRunesword20260913/Modules20260919'
SOURCE='/Game/Weapons/AzureRunesword20260913'
S=u.ModelingService; L=u.EditorAssetLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before authoring rune sword modules; keep the editor open.')
receipt=[]; handles=[]
def done(r):
    if not r.success: raise RuntimeError(r.message)
    receipt.append({'asset':str(r.asset_path),'operation':str(r.message)})
    return r
def load(path,skin=False):
    r=done(S.load_mesh_from_skeletal_mesh(path) if skin else S.load_mesh_from_static_mesh(path))
    handles.append(r.handle); return r.handle
def export(asset,name,skin=False):
    task=u.AssetExportTask();task.object=asset;task.filename=str(OUT/(name+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.SkeletalMeshExporterFBX() if skin else u.StaticMeshExporterFBX()
    task.options=u.FbxExportOption();task.options.ascii=False;task.options.level_of_detail=False;task.options.collision=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('FBX export failed: '+name)
    receipt.append({'asset':asset.get_path_name(),'export':task.filename})
    return asset
try:
    # The existing interfaces are kept in canonical centimetres. The whole
    # jewel seat belongs to the guard; the lower flare belongs to the pommel.
    specs={'blade_1':(12.5,None,0.),'guard':(-4.,12.5,0.),'grip':(-19.5,-4.,-4.),'pommel':(None,-19.5,-19.5)}
    material=u.load_asset(SOURCE+'/SM_AzureRunesword').get_material(0)
    catalog={'version':1,'weapon':'ue_rune_sword','interface':'azure_hilt_v1','drive_bone':'WPN_root','slots':{}}
    rows=[]
    for slot,(low,high,pivot) in specs.items():
        h=load(SOURCE+'/SM_AzureRunesword')
        if low is not None:done(S.plane_cut(h,u.Transform(location=u.Vector(0,0,low)),True,True))
        if high is not None:done(S.plane_cut(h,u.Transform(location=u.Vector(0,0,high)),True,False))
        if pivot:done(S.translate_mesh(h,u.Vector(0,0,-pivot)))
        name='SM_RuneSword_'+('Blade' if slot=='blade_1' else slot.title())+'_factory'
        path=D+'/'+name
        if not L.does_asset_exist(path):done(S.save_mesh_to_static_mesh(h,path,False,False,False,False))
        done(S.set_asset_materials(path,material.get_path_name(),True))
        asset=export(u.load_asset(path),name)
        spec={'mesh':asset.get_path_name(),'location_cm':[0,0,pivot],'interface':'azure_hilt_v1'}
        if slot=='blade_1':spec['rune_dimensions_cm']=[10.6,10,63]
        catalog['slots'][slot]={'factory':spec}
        rows.append({'slot':slot,'id':'factory','mesh':name,'location_cm':spec['location_cm']})
    # Keep the actual current hand mesh, weights, bone attributes and materials.
    donor=u.load_asset(SOURCE+'/SK_AzureRunesword_Manny')
    h=load(donor.get_path_name(),True)
    bones={b.name:b for b in S.list_bones(h)}
    root=bones['WPN_root'].mesh_transform
    scale=root.scale3d
    catalog['bone_mount']={'location_cm':[0,0,0],'rotation_xyzw':[0,0,0,1],'scale':[1/scale.x,1/scale.y,1/scale.z]}
    blade=catalog['slots']['blade_1']['factory']
    for name,key in [('Blade_Base','trace_base_cm'),('Blade_Tip','trace_tip_cm')]:
        p=root.inverse_transform_location(bones[name].mesh_transform.translation)
        blade[key]=[p.x*scale.x,p.y*scale.y,p.z*scale.z]
    slots=donor.get_editor_property('materials')
    for i,slot in enumerate(slots):
        if 'AzureRunesword' in str(slot.material_slot_name) or (slot.material_interface and 'AzureRunesword' in slot.material_interface.get_name()):
            count=S.select_by_material_id(h,'rune_sword_surface',i)
            if count<=0:raise RuntimeError('Sword material has no selected geometry')
            done(S.delete_faces(h,'rune_sword_surface'))
    name='SK_RuneSword_Arms'
    done(S.save_mesh_to_skeletal_mesh(h,D+'/'+name,donor.skeleton.get_path_name(),False,False))
    arms=u.load_asset(D+'/'+name)
    # Retain slot names as well as material interfaces for the equipment skin layer.
    arms.set_editor_property('materials',slots)
    arms.set_editor_property('positive_bounds_extension',u.Vector(120,120,120))
    arms.set_editor_property('negative_bounds_extension',u.Vector(120,120,120))
    if not L.save_loaded_asset(arms,False):raise RuntimeError('Unable to save arm carrier')
    export(arms,name,True);catalog['arms_mesh']=arms.get_path_name()
    (P/'catalog_base.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    (P/'exports.json').write_text(json.dumps({'parts':rows,'arms':name,'material':material.get_path_name(),'cuts_cm':specs},indent=2),encoding='utf-8')
    (P/'base_authoring_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('RUNE_SWORD_BASE_MODULES_AUTHORED')
finally:
    for h in handles:S.release_mesh(h)
