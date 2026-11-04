"""Import two continuous R5 heads and three approved-master shared icons."""
import ast,json,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
PROJECT=P.parents[3]
DEST='/Game/Weapons/TacticalHatchet20261101/ModulesV1'
ICON_DEST='/Game/ColdSteelData/AttachmentIcons20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
entries=json.loads((P/'parts.json').read_text('utf-8'))
jobs=json.loads((P/'icon_deployments.json').read_text('utf-8'))
receipt={'complete':False,'assets':[],'parts':[],'icons':[],'runtime_tested':False}
owned={DEST+'/'+e['object'] for e in entries}
owned.update(DEST+'/Materials/'+e['object'].replace('SM_','M_',1) for e in entries)
owned.update(DEST+'/Textures/'+Path(p).stem for e in entries for p in e['textures'].values())
owned.update(ICON_DEST+'/'+j['key'] for j in jobs)
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&owned:raise RuntimeError('Owned packages contain unsaved editor changes; preserved: '+str(dirty&owned))
for package in owned:
    relative=Path(package.removeprefix('/Game/')+'.uasset')
    old=PROJECT/'Content'/relative;backup=P/'Before/Assets'/relative
    if old.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,backup)
helper=P.parents[1]/'ModulesV1/import_modules.py'
source=helper.read_text('utf-8-sig').replace("set_editor_property('two_sided',True)","set_editor_property('two_sided',False)")
tree=ast.parse(source)
functions=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'save','imported','material'}],type_ignores=[])
exec(compile(functions,str(helper),'exec'),globals())
ui=u.FbxImportUI();ui.import_mesh=True;ui.import_as_skeletal=False;ui.import_materials=False;ui.import_textures=False;ui.import_animations=False
ui.automated_import_should_detect_type=False;ui.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
settings=ui.static_mesh_import_data;settings.combine_meshes=True;settings.auto_generate_collision=False
settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;settings.generate_lightmap_u_vs=False
for entry in entries:
    mat=material(entry)
    mesh=imported(entry['fbx'],entry['object'],DEST,ui)
    for i in range(len(mesh.static_materials)):mesh.set_material(i,mat)
    nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True;mesh.set_editor_property('nanite_settings',nanite)
    if not u.TacticalHatchetImportLibrary.finalize_mesh(mesh):raise RuntimeError('Author normals/tangents finalization failed: '+entry['id'])
    u.EditorAssetLibrary.set_metadata_tag(mesh,'HatchetInterface','R5 continuous forged taper and convex grind; connected stock neck; stock +11.5cm mating end')
    u.EditorAssetLibrary.set_metadata_tag(mesh,'ModelRevision',entry['model_revision'])
    u.EditorAssetLibrary.set_metadata_tag(mesh,'MaterialSource','Original hatchet body and cutting edge PBR')
    save(mesh)
    receipt['parts'].append({'slot':'blade_1','id':entry['id'],'mesh':mesh.get_path_name(),'material':mat.get_path_name(),
        'material_slot_names':[str(s.get_editor_property('material_slot_name')) for s in mesh.static_materials],
        'location_cm':entry['origin_cm'],'trace_base_cm':entry['trace_base_cm'],'trace_tip_cm':entry['trace_tip_cm']})
for job in jobs:
    tex=imported(job['source'],job['key'],ICON_DEST)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('max_texture_size',1024)
    save(tex);receipt['icons'].append(tex.get_path_name())
receipt['assets']=list(dict.fromkeys(receipt['assets']));receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
u.log('HATCHET_CONTINUOUS_R5_SAVED heads='+str(len(receipt['parts']))+' icons='+str(len(receipt['icons']))+' assets='+str(len(receipt['assets'])))
