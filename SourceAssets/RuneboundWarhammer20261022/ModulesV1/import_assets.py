"""Import fitted factory/common modules and shaft-local runes, then publish the recipe."""
import unreal as u,json,sys,re
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D='/Game/Weapons/RuneboundWarhammer20261022/ModulesV1'
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
receipt={'complete':False,'tested':False,'assets':[]}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+str(asset))
    if asset.get_path_name() not in receipt['assets']:receipt['assets'].append(asset.get_path_name())
    record();return asset
def imp(source,name,folder,options=None):
    asset=u.load_asset(folder+'/'+name)
    if asset:return asset
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False
    if options:task.options=options
    A.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+str(source))
    return asset

record()
materials={
 'M_RuneboundWarhammerSurface':'/Game/Weapons/RuneboundWarhammer20261022/Materials/M_RuneboundWarhammerSurface',
 'M_CommonHammerHeadSteel':'/Game/Weapons/CommonHammerHeads20261014/Materials/M_CommonHammerHeadSteel',
 'M_CommonHammerSeatDarkSteel':'/Game/Weapons/CommonHammerSeats20261014/BuildV1/Materials/M_CommonHammerSeatDarkSteel',
 'M_CommonHammerSeatDamping':'/Game/Weapons/CommonHammerSeats20261014/BuildV1/Materials/M_CommonHammerSeatDamping',
 'M_CommonHammerPommelTurned':'/Game/Weapons/CommonHammerPommels20261014/BuildV1/Materials/M_CommonHammerPommelTurned',
}
for name in ('M_HammerGripWoven','M_HammerGripLeather','M_HammerGripDarkLeather'):
    materials[name]='/Game/Weapons/CommonHammerGrips20261014/BuildV1/Materials/'+name
materials={key:u.load_asset(value) for key,value in materials.items()}
if any(not v for v in materials.values()):raise RuntimeError('A shared PBR material is missing')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
factory=json.loads((P/'exports.json').read_text(encoding='utf-8-sig'))['parts']
fitted=json.loads((P/'adapted_exports.json').read_text(encoding='utf-8-sig'))['parts']
for row in factory+fitted:
    mesh=imp(P/'Export'/(row['mesh']+'.fbx'),row['mesh'],D,opt)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'(?:[._]\d{3})+$','',str(slot.material_slot_name))
        if key not in materials:raise RuntimeError('Unknown fitted-part material: '+key)
        mesh.set_material(i,materials[key])
    # Original module surfaces retain the authored normals and full RT fallback.
    # The shared-material alternatives retain their existing LOD0 rendering policy.
    if row['id']=='factory':
        settings=mesh.get_editor_property('nanite_settings')
        # The bare shaft keeps the existing hammer's conventional overlay path.
        settings.enabled=row['slot']!='shaft';settings.explicit_tangents=True
        settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.
        mesh.set_editor_property('nanite_settings',settings)
    save(mesh)

source=u.load_asset('/Game/Weapons/SteelWarhammer20261014/Runes/ShaftWrapV2/M_SilverRuneSurface_WarhammerShaftV2')
name='M_SilverRuneSurface_RuneboundWarhammerShaftV1'
rune=u.load_asset(D+'/Runes/'+name)
if not rune:rune=A.duplicate_asset(name,D+'/Runes',source)
if not rune:raise RuntimeError('Cannot create host-local rune material')
custom=next(n for n in E.get_material_expressions(rune) if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
code=custom.get_editor_property('code')
code=code.replace('float artHeight = 37.5;', 'float artHeight = 33.5;')
code=code.replace('float shaftStart = -39.5;', 'float shaftStart = -35.5;')
code=code.replace('float2(-.088, -.094)', 'float2(-.0445214100, .1056659501)')
custom.set_editor_property('code',code)
custom.set_editor_property('description','Runebound shaft-local wrap, weapon Z 42.5 to 76 cm; shared masks and palettes')
rune.set_editor_property('used_with_skeletal_mesh',False)
if E.recompile_material(rune):raise RuntimeError('Rune material compilation failed')
save(rune)
(P/'shaft_runes.hlsl').write_text(code,encoding='utf-8')

icons=ROOT/'Content/ColdSteelData/AttachmentIcons20260913';folder='/Game/ColdSteelData/AttachmentIcons20260913'
for suffix in ('category_rune','rune_false'):
    import shutil
    shutil.copy2(icons/(suffix+'.png'),icons/('ue_runebound_warhammer_'+suffix+'.png'))
# M4GunsmithLayout consumes these staged PNGs directly through ImportFileAsTexture2D.
# No additional persistent Texture2D packages are part of this icon contract.
sys.path.insert(0,str(P))
from register import publish
publish()
receipt.update(complete=True,factory_modules=len(factory),fitted_common_modules=len(fitted),
    shared_runes=5,animation_assets_modified=0,recipe_published=True,icons_storage='staged PNG')
record();print('RUNEBOUND_HAMMER_MODULAR_IMPORT_COMPLETE '+json.dumps(receipt))
