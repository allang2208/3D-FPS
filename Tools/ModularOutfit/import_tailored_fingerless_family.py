"""Save all selected native glove meshes, then publish only the brown item."""
import json
import sys
import hashlib
import shutil
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/ModularOutfit'))
import import_tailored_fingerless_candidate as lib
R=P/'SourceAssets/ModularOutfit20260927/TailoredFingerlessV1'
DEST='/Game/Characters/ModularOutfit20260924/TailoredFingerlessV1'
E=lib.E;A=lib.A


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def import_pickup(material):
    folder=DEST+'/Pickups';name='SM_TailoredFingerless_Pickup';E.make_directory(folder)
    task=u.AssetImportTask();task.filename=str(R/(name+'.fbx'));task.destination_name=name;task.destination_path=folder
    task.automated=True;task.replace_existing=True;task.save=False
    options=u.FbxImportUI();options.set_editor_property('import_as_skeletal',False);options.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
    options.set_editor_property('automated_import_should_detect_type',False);options.set_editor_property('import_materials',False);options.set_editor_property('import_textures',False)
    options.get_editor_property('static_mesh_import_data').set_editor_property('combine_meshes',True);task.options=options
    A.import_asset_tasks([task]);mesh=lib.load(folder+'/'+name);mesh.set_material(0,material)
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    reduction=u.StaticMeshReductionOptions();reduction.set_editor_property('auto_compute_lod_screen_size',False)
    settings=[]
    for percent,screen in ((1.,1.),(.5,.18),(.35,.075)):
        setting=u.StaticMeshReductionSettings();setting.set_editor_property('percent_triangles',percent);setting.set_editor_property('screen_size',screen);settings.append(setting)
    reduction.set_editor_property('reduction_settings',settings);editor.set_lods(mesh,reduction)
    lib.save(mesh)
    return mesh


def publish(receipt):
    cfgpath=P/'Content/ColdSteelData/modular_outfits.json';itempath=P/'Content/ColdSteelData/items.json'
    cfg=read(cfgpath);items=read(itempath);old=cfg['items']['ue_field_gloves']
    if set(old['rig_meshes'])!=set(receipt['profiles']):raise RuntimeError('The active profile set changed; keep the saved family and update its scope before publication')
    before=R/'BeforePublication';before.mkdir(exist_ok=True)
    snapshot=before/'brown-item.json'
    if not snapshot.exists():snapshot.write_text(json.dumps(dict(recipe=old,item=items['ue_field_gloves']),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    icon=P/'Content/ColdSteelData'/items['ue_field_gloves']['ue_icon']
    if not (before/icon.name).exists():shutil.copy2(icon,before/icon.name)
    old.update(rig_meshes={k:v['standalone'] for k,v in receipt['profiles'].items()},
               skin_meshes={k:v['combined'] for k,v in receipt['profiles'].items()},
               material=receipt['materials']['Shared'],covers=[],glove_in_base=True,appearance_family='TailoredFingerlessV1')
    item=items['ue_field_gloves'];item['world_mesh']=receipt['pickup'];item['world_material']=receipt['materials']['Shared']
    # Retain name, stats, description snapshots, slots, IDs and save identity.
    shutil.copy2(R/'TailoredFingerless_Icon.png',icon)
    cfgpath.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    itempath.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    result=dict(receipt,item='ue_field_gloves',icon=str(icon),active_equipment_changed=True,animations_changed=0,
                balance_changed=False,runtime_tested=False,source='TailoredFingerlessV1',configuration_refresh='next game session')
    (R/'published.json').write_text(json.dumps(result,indent=2)+'\n')
    print('TAILORED_FAMILY_PUBLISHED',len(receipt['profiles']),flush=True)


def main():
    entries=read(R/'manifest.json');groups=sorted({e['material_group'] for e in entries})
    cfg=read(P/'Content/ColdSteelData/modular_outfits.json')
    if set(cfg['items']['ue_field_gloves']['rig_meshes'])!={e['profile'] for e in entries}:raise RuntimeError('Native profile scope changed')
    saved=R/'Saved';saved.mkdir(exist_ok=True);mats={};profiles={}
    for group in groups:
        folder=R/'Textures' if group=='Shared' else R/'Textures'/group
        mats[group]=lib.material(folder,DEST+'/Materials/'+group)
    for entry in entries:
        name=entry['profile'];mat=mats[entry['material_group']]
        raw=Path(entry['authored']).read_bytes();skinraw=Path(entry['source_skin']).read_bytes()
        sha=hashlib.sha256(raw+skinraw+mat.get_path_name().encode()).hexdigest();record=saved/(name+'.json')
        if record.exists():
            old=read(record)
            if old.get('sha256')==sha and E.does_asset_exist(old['standalone']) and E.does_asset_exist(old['combined']):
                profiles[name]=old;continue
        glove=json.loads(raw);standalone=lib.build_mesh(glove,'SK_'+name+'_TailoredFingerless',[mat],['FingerlessGloveLeather'],DEST)
        skin=json.loads(skinraw);skin['profile']=name;skin['contract']='Tailored fingerless and exposed skin assembly; native shared boundary; original animation'
        source=lib.load(skin['source']);slots=source.get_editor_property('materials');index=len(slots);start=len(skin['positions'])
        skin['positions'].extend(glove['positions']);skin['weights'].extend(glove['weights'])
        skin['triangles'].extend([[v+start for v in f] for f in glove['triangles']]);skin['normals'].extend(glove['normals'])
        skin['triangle_materials'].extend([index]*len(glove['triangles']))
        skin['colors'].extend([[[0,0,0,1]]*3 for _ in glove['triangles']])
        for key in [k for k in skin if k.startswith('uv')]:skin[key].extend(glove.get(key,[[[0,0]]*3 for _ in glove['triangles']]))
        combined=lib.build_mesh(skin,'SK_'+name+'_TailoredFingerlessSkin',[m.material_interface for m in slots]+[mat],
                                [m.material_slot_name for m in slots]+['FingerlessGloveLeather'],DEST)
        row=dict(standalone=standalone.get_path_name(),combined=combined.get_path_name(),material=mat.get_path_name(),lods=3,sha256=sha)
        record.write_text(json.dumps(row,indent=2)+'\n');profiles[name]=row
        print('TAILORED_PROFILE_PAIR_SAVED',name,flush=True)
    pickup=import_pickup(mats['Shared'])
    receipt=dict(profiles=profiles,materials={g:m.get_path_name() for g,m in mats.items()},pickup=pickup.get_path_name(),new_animations=0,runtime_tested=False)
    (R/'saved-assets.json').write_text(json.dumps(receipt,indent=2)+'\n')
    publish(receipt)


if __name__=='__main__':main()
