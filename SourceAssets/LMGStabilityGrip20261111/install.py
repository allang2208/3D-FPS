"""Save new fitted parts/pose profiles and reuse the existing framed artwork."""
from pathlib import Path
import unreal as u,json,gzip,hashlib,shutil,zipfile
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
ROOT='/Game/Weapons/LMGStabilityGrip20261111';receipt={'saved':{},'complete':False,'runtime_tested':False}
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE remains running; nothing saved')
def saved(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    package=a.get_path_name().split('.')[0];path=PROJECT/'Content'/(package.removeprefix('/Game/')+'.uasset')
    receipt['saved'][package]=hashlib.sha256(path.read_bytes()).hexdigest()
    (HERE/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
geo=json.loads((HERE/'geometry.json').read_text())
for key,spec in geo['parts'].items():
    task=u.AssetImportTask();task.filename=spec['file'];task.destination_path=ROOT;task.destination_name=spec['asset'].rsplit('/',1)[-1];task.automated=True;task.replace_existing=True;task.save=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
    task.options=opt;A.import_asset_tasks([task]);asset=u.load_asset(spec['asset'])
    if not asset:raise RuntimeError('Import failed '+spec['asset'])
    for i,m in enumerate(asset.static_materials):
        slot=str(m.material_slot_name);path=spec['materials'].get(slot)
        if not path:raise RuntimeError('Unbound imported material '+slot)
        mat=u.load_asset(path)
        if not mat:raise RuntimeError('Missing source material '+path)
        asset.set_material(i,mat)
    saved(asset)
for key,name in [('M249','DA_M249_Handguard'),('LMG201','DA_LMG201_Stability'),('PKM','DA_PKM_Stability')]:
    payload=json.load(gzip.open(HERE/(key+'_profile.json.gz'),'rt'));path=ROOT+'/'+name
    asset=u.load_asset(path)
    if not asset:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
        asset=A.create_asset(name,ROOT,u.WeaponGripProfile,factory)
    if not asset or not asset.set_shared_clips_from_json(json.dumps(payload)):raise RuntimeError('Profile import failed '+path)
    saved(asset)
icons=PROJECT/'Content/ColdSteelData/AttachmentIcons20260913';source=HERE/'Icons';source.mkdir(exist_ok=True)
shared='underbarrel_lmg_stability_foregrip';bare='ue_m249_underbarrel_false'
if not (source/(shared+'.png')).exists():shutil.copy2(icons/'FramedFirearms'/ (bare+'.png'),source/(shared+'.png'))
shutil.copy2(icons/'FramedFirearms/underbarrel_false.png',source/(bare+'.png'))
backup=HERE/'icons-before.zip'
if not backup.exists():
    with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as z:
        for sub in ['', 'FramedFirearms/']:
            for ext in ['.png','.uasset']:
                p=icons/sub/(bare+ext)
                if p.exists():z.write(p,str(p.relative_to(PROJECT)))
for sub in ['', 'FramedFirearms/']:
    for name in [shared,bare]:
        dst=icons/sub/(name+'.png');shutil.copy2(source/(name+'.png'),dst)
        task=u.AssetImportTask();task.filename=str(dst);task.destination_path=('/Game/ColdSteelData/AttachmentIcons20260913/'+sub).rstrip('/');task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
        A.import_asset_tasks([task]);asset=u.load_asset(task.destination_path+'/'+name)
        if not asset:raise RuntimeError('Icon import failed '+name)
        asset.srgb=True;asset.lod_group=u.TextureGroup.TEXTUREGROUP_UI;asset.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;asset.never_stream=True;asset.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;saved(asset)
receipt['complete']=True;(HERE/'install_receipt.json').write_text(json.dumps(receipt,indent=2));print('Saved',len(receipt['saved']),'assets; runtime testing remains manual.')
