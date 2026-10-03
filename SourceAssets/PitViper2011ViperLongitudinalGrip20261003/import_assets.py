"""Replace only the installed VIP skin, its private maps and dedicated icon."""
import json,re,shutil,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1]
auth=json.loads((O/'authoring.json').read_text(encoding='utf8'))
D='/Game/Weapons/PitViper2011/VipGrip20261002'
SURFACE='/Game/Weapons/PitViper2011/SurfaceRefine20261003'
KEY='ue_pit_viper2011_reargrip_pit_viper_vip_scales'
ICON=D+'/Icons/T_'+KEY
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
targets={auth['mesh'],auth['active_surface'],ICON}
targets.update(SURFACE+'/Textures/'+Path(f).stem for f in auth['quiet_textures'].values())
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong production project')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets&dirty:raise RuntimeError('Preserve unsaved VIP grip packages '+str(sorted(targets&dirty)))
for path in targets:
    source=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=O/'Before/Content'/(path.removeprefix('/Game/')+'.uasset')
    if source.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
receipt={'saved':[],'part':'pit_viper_vip_scales','revision':auth['revision'],
    'game_tested':False,'acceptance_rendered':False,'native_build_required':False,'stats_changed':False}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing existing VIP dependency '+path)
    return obj
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('VIP save failed '+obj.get_path_name())
    if obj.get_path_name() not in receipt['saved']:receipt['saved'].append(obj.get_path_name())
    record();return obj
def import_file(file,folder,name,options=None):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task]);return load(folder+'/'+name)
old=load(auth['mesh'])
canon=lambda name:re.sub(r'[._]\d{3}$','',str(name))
materials={canon(s.material_slot_name):s.material_interface for s in old.static_materials}
material=load(auth['active_surface'])
textures={}
for kind,file in auth['quiet_textures'].items():
    tex=import_file(file,SURFACE+'/Textures',Path(file).stem)
    tex.srgb=kind=='BaseColor'
    tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_BC7
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON
    tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE;tex.filter=u.TextureFilter.TF_TRILINEAR;tex.never_stream=False
    if kind=='Normal':tex.flip_green_channel=True
    E.set_metadata_tag(tex,'GripSurfaceRevision',auth['revision']);save(tex);textures[kind]=tex
for node in L.get_material_expressions(material):
    if not isinstance(node,u.MaterialExpressionTextureSample) or not node.texture:continue
    path=node.texture.get_path_name().split('.')[0]
    for kind,tex in textures.items():
        if path.endswith('_'+kind):
            node.texture=tex
            node.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
            break
L.recompile_material(material);E.set_metadata_tag(material,'GripSurfaceRevision',auth['revision']);save(material)
flag='Interchange.FeatureFlags.Import.FBX';oldflag=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.generate_lightmap_u_vs=False;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=import_file(auth['fbx'],D,auth['name'],opt);slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):
        label=canon(slot.material_slot_name)
        slot.material_interface=material if label=='M_PitViper2011_VipViperGrip' else materials[label]
        slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    if subsystem:
        settings=subsystem.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;subsystem.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'SourceAttribution',auth['provenance']);E.set_metadata_tag(mesh,'GripSurfaceRevision',auth['revision'])
    E.set_metadata_tag(mesh,'GripSurfaceFrame',auth['frame']);save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(oldflag))
content=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/(KEY+'.png')
backup=O/'Before/Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/(KEY+'.png')
if content.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(content,backup)
shutil.copy2(O/'Icons'/(KEY+'.png'),content)
tex=import_file(content,D+'/Icons','T_'+KEY);tex.srgb=True
tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI
tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;tex.never_stream=True;save(tex)
receipt.update(status='imported_and_saved',mesh=mesh.get_path_name(),fbx=auth['fbx'],
    fbx_sha256=hashlib.sha256(Path(auth['fbx']).read_bytes()).hexdigest(),
    materials={str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},
    icon={'png':str(content),'asset':tex.get_path_name()},
    textures={k:v.get_path_name() for k,v in textures.items()},runtime_mount_changed=False)
record()
legacy=O.parent/'PitViper2011VipGrip20261002/import_receipt.json'
if legacy.exists():
    r=json.loads(legacy.read_text(encoding='utf8'));r['longitudinal_revision']=receipt
    legacy.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
print('VIP_LONGITUDINAL_GRIP_IMPORTED_AND_SAVED',flush=True)
