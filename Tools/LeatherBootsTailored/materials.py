"""Production PBR surfaces and the existing robe draw-only visibility contract."""
import hashlib,importlib.util,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def save(a):
    if not a.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside boot upgrade scope')
    a.modify()
    if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def create():
    sha=hashlib.sha256(Path(__file__).read_bytes()+(R/'surfaces.json').read_bytes()).hexdigest();path=R/'materials.json'
    if path.exists():
        old=read(path)
        if old.get('completed') and old.get('revision')==sha and all(E.does_asset_exist(p) for p in old['materials']+old['robe_materials']+old['textures']):return old
    textures=[]
    for family in ('BootLeather','BootReinforced','BootRubber','BootWelt'):
        for channel in ('BaseColor','Normal','ORM'):
            t=u.AssetImportTask();t.filename=str(R/'Textures'/(family+'_'+channel+'.png'));t.destination_path=DEST+'/Textures';t.destination_name='T_'+family+'_'+channel;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+t.destination_name)
            if not tex:raise RuntimeError('Texture import '+t.filename)
            for k,v in dict(srgb=channel=='BaseColor',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT,flip_green_channel=channel=='Normal',never_stream=False,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE).items():tex.set_editor_property(k,v)
            tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if channel=='Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR if channel=='ORM' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
            if channel=='Normal':tex.set_editor_property('normalize_normals',True)
            save(tex);textures.append(tex.get_path_name())
    sys.path.insert(0,str(P/'Tools/RangerLeatherPants'));factory=module('boot_material_factory','Tools/RangerLeatherPants/integration_materials.py');factory.DEST=DEST
    m=factory.material;s=read(R/'surfaces.json')
    mats=[m('AgedSteel',color=s['metal_linear_color'],rough=.48,metal=1),m('BootLeather','BootLeather'),m('RubberOutsole','BootRubber'),m('WaxedThread',color=s['thread_linear_color'],rough=.82),m('ReinforcedLeather','BootReinforced'),m('StackedWelt','BootWelt'),m('DarkLining','BootLeather')]
    sys.path.insert(0,str(P/'Tools/BlueMageRobe'));import hem_materials
    hem_materials.DEST=DEST+'/RobeMaterials';robe=[hem_materials.make(a).get_path_name() for a in mats]
    result=dict(completed=True,revision=sha,materials=[a.get_path_name() for a in mats],robe_materials=robe,textures=textures,normal_flip_green=True,streaming=True,runtime_tested=False);write(path,result);return result
