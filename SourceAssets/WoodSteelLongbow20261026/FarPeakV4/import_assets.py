"""Save the exclusive bow body, its owned finishes and its actual-model UI icon."""
from pathlib import Path
import json, hashlib, shutil
import unreal as u
P=Path(__file__).parent
BASE='/Game/Weapons/WoodSteelLongbow20261026'
DEST=BASE+'/FarPeakV4'
ICON='/Game/ColdSteelData/AttachmentIcons20260913/FramedBows'
NAME='SK_HighlandLongbow_FarPeak'
ICON_NAME='bow_woodsteel_riser_highland_far_peak'
E=u.EditorAssetLibrary; A=u.AssetToolsHelpers.get_asset_tools(); L=u.MaterialEditingLibrary
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'sources':{},'gameplay_tested':False}
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(DEST+'/') or package.get_name()==ICON+'/'+ICON_NAME:
        raise RuntimeError('Preserving unsaved package '+package.get_name())
def save(asset,source=None):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Package save failed '+str(asset))
    r['saved'][asset.get_name()]=asset.get_path_name()
    if source:r['sources'][asset.get_name()]=hashlib.sha256(source.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
    print('FAR_PEAK_SAVED '+asset.get_path_name(),flush=True)
def existing(name,folder=DEST):
    if name in r['saved']:return u.load_asset(r['saved'][name])
    if E.does_asset_exist(folder+'/'+name):raise RuntimeError('Preserving existing unowned asset '+folder+'/'+name)
    return None
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
materials={name:u.load_asset(BASE+'/'+name) for name in ['M_WoodSteelLongbow_PBR','M_WoodSteelLongbow_Steel']}
for finish,color,metal,rough in [('BlackenedSteel',(.15,.19,.21),.85,.36),('RubbedBronze',(.30,.18,.07),.75,.4),('LaminateEdge',(.20,.085,.029),0,.65)]:
    name='M_FarPeak_'+finish;m=existing(name)
    if not m:
        m=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
        b=node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*color,1))
        L.connect_material_property(b,'',u.MaterialProperty.MP_BASE_COLOR)
        for value,prop in [(metal,u.MaterialProperty.MP_METALLIC),(rough,u.MaterialProperty.MP_ROUGHNESS)]:
            L.connect_material_property(node(m,u.MaterialExpressionConstant,r=value),'',prop)
        L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.recompile_material(m);save(m)
    materials[name]=m
source=P/'Export'/(NAME+'.fbx');mesh=existing(NAME)
if not mesh:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_mesh=True;options.import_as_skeletal=True;options.import_animations=False
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
    options.skeleton=u.load_asset(BASE+'/SK_WoodSteelLongbow_Original_Skeleton')
    if not options.skeleton:raise RuntimeError('Existing longbow skeleton is unavailable')
    d=options.skeletal_mesh_import_data
    d.set_editor_property('update_skeleton_reference_pose',False);d.set_editor_property('use_t0_as_ref_pose',False)
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=NAME
    task.automated=True;task.save=False;task.options=options
    A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+NAME)
    if not mesh:raise RuntimeError('Far Peak mesh import failed')
    slots=list(mesh.get_editor_property('materials'))
    for i,slot in enumerate(slots):
        name=str(slot.material_slot_name)
        if name not in materials or not materials[name]:raise RuntimeError('Unresolved finish '+name)
        slot.set_editor_property('material_interface',materials[name]);slots[i]=slot
    mesh.set_editor_property('materials',slots)
    save(mesh,source)
    r['skeleton']=mesh.skeleton.get_path_name();r['materials']=[str(s.material_interface.get_path_name()) for s in slots]
tex=existing(ICON_NAME,ICON)
if not tex:
    png=P/(ICON_NAME+'.png')
    target=Path('D:/FPS3D/FPSGAME/Content')/ICON.removeprefix('/Game/')/(ICON_NAME+'.png')
    shutil.copy2(png,target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_path=ICON;task.destination_name=ICON_NAME
    task.automated=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(ICON+'/'+ICON_NAME)
    if not tex:raise RuntimeError('Far Peak icon import failed')
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;tex.srgb=True;tex.max_texture_size=1024
    tex.set_editor_property('never_stream',True);save(tex,png)
r['complete']=True
receipt.write_text(json.dumps(r,indent=2),encoding='utf-8')
print('FAR_PEAK_IMPORT_COMPLETE',flush=True)
