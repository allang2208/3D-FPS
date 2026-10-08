"""Import the approved picture unchanged; adapt the owned mode-8 material branch."""
from pathlib import Path
import hashlib
import json
import shutil
import unreal as u

P=Path(__file__).resolve().parent
SOURCE=P.parent
ROOT=SOURCE.parents[1]
REV='BladeTalismanV4'
IMAGE=P/'Zhenmo_Blade_Talisman_V4_Concept.png'
MASK='/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Textures/T_Mask_zhenmo_rune'
E,L=u.MaterialEditingLibrary,u.EditorAssetLibrary


def replace_branch(code,new):
    marker='// Zhenmo mode 8:'
    start=code.find(marker)
    if start<0:raise RuntimeError('Active material lacks the owned Zhenmo branch')
    opening=code.find('{',start)
    if opening<0:raise RuntimeError('Zhenmo branch lacks an opening brace')
    depth=0
    for end in range(opening,len(code)):
        if code[end]=='{':depth+=1
        elif code[end]=='}':
            depth-=1
            if depth==0:return code[:start]+new.rstrip()+code[end+1:]
    raise RuntimeError('Unterminated Zhenmo branch')


def backup(package):
    relative=package.split('.')[0].removeprefix('/Game/')+'.uasset'
    source=ROOT/'Content'/relative
    dest=P/'Before/Content'/relative
    if source.exists() and not dest.exists():
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dest)


def install():
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('Exit PIE before saving the approved talisman')
    catalog=json.loads((ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json').read_text(encoding='utf-8-sig'))
    temporal=json.loads((ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json').read_text(encoding='utf-8-sig'))
    temporal=temporal.get('materials',temporal)
    active={v for row in catalog['slots']['blade_1'].values() for v in row.get('materials',{}).values()}
    # Keep the predecessor material used by the existing full-authoring recipe in
    # sync as well as the currently bound Jingang extension and temporal variants.
    previous=json.loads((SOURCE/'import_receipt.json').read_text(encoding='utf-8-sig'))
    paths=active|set(previous['material_bindings'].values())
    paths.update(temporal[p] for p in list(paths) if p in temporal)
    paths.update(p for p in previous['assets'] if '/Materials/M_XuanChiBladeRuneSurface_' in p)
    targets={p.split('.')[0] for p in paths}|{MASK}
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if str(package.get_name()) in targets:
            raise RuntimeError('Preserving unsaved package '+str(package.get_name()))
    new=(SOURCE/'zhenmo_emission.hlsl').read_text(encoding='utf-8')
    materials=[]
    for path in sorted(paths):
        material=u.load_asset(path)
        if not material:raise RuntimeError('Missing blade material '+path)
        nodes=[n for n in E.get_material_expressions(material)
               if isinstance(n,u.MaterialExpressionCustom) and '// Zhenmo mode 8:' in n.get_editor_property('code')]
        if len(nodes)!=1:raise RuntimeError('Expected one mode-8 expression in '+path)
        node=nodes[0]
        materials.append((material,node,replace_branch(node.get_editor_property('code'),new)))
        backup(path)
    backup(MASK)
    folder,name=MASK.rsplit('/',1)
    task=u.AssetImportTask()
    task.filename=str(IMAGE)
    task.destination_path=folder
    task.destination_name=name
    task.automated=True
    task.replace_existing=True
    task.save=False
    task.factory=u.TextureFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=u.load_asset(MASK)
    if not texture:raise RuntimeError('Approved talisman texture import failed')
    # A single editor notification finishes the import's async texture build
    # before changing compression, size and mip settings together.
    texture.set_editor_properties({
        'srgb':False,
        'compression_settings':u.TextureCompressionSettings.TC_GRAYSCALE,
        'power_of_two_mode':u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO,
        'max_texture_size':4096,
        'never_stream':False,
        'mip_gen_settings':u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP,
        'address_x':u.TextureAddress.TA_CLAMP,
        'address_y':u.TextureAddress.TA_CLAMP})
    L.set_metadata_tag(texture,'ZhenmoBladeRevision',REV)
    sha=hashlib.sha256(IMAGE.read_bytes()).hexdigest()
    L.set_metadata_tag(texture,'ZhenmoBladeSourceSHA256',sha)
    receipt={'complete':False,'revision':REV,'source_sha256':sha,'saved_assets':[],
             'source_pixels':[724,2172],'source_image_unchanged':True,
             'runtime_tested':False,'visual_tested':False}
    def record():
        (P/'asset_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def save(asset):
        if not L.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed '+asset.get_path_name())
        receipt['saved_assets'].append(asset.get_path_name());record()
    save(texture)
    for material,node,code in materials:
        node.set_editor_property('code',code)
        errors=E.recompile_material(material)
        if errors:raise RuntimeError('Blade material compile failed '+str(errors))
        L.set_metadata_tag(material,'ZhenmoBladeRevision',REV)
        save(material)
    receipt['complete']=True
    record()
    print('ZHENMO_TALISMAN_V4_SAVED '+json.dumps(receipt),flush=True)


if __name__=='__main__':install()
