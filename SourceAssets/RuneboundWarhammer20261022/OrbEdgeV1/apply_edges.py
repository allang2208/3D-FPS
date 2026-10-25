"""Enhance only the two existing orb shell materials, in the current editor."""
import ast,json,shutil,datetime
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;FAMILY=P.parent;ROOT=FAMILY.parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End the current preview before saving shell materials')
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
receipt={'complete':False,'assets':[],'gpu_compilation':{},'visual_tested':False,'timestamp':stamp,
         'shell_opacity':{'center':.18,'edge':.90},'fresnel_exponents':[2.2,7.],
         'changes':'Colored translucent shoulder plus narrow emissive rim, stronger specular reflection, retained clear center'}
def record():
    (P/'saved_edges.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
helpers=ast.parse((FAMILY/'RuneAndBellRefinement20261024/install_assets.py').read_text('utf-8'))
defs=compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'<material_helpers>','exec')
for folder,name,owner,end_name in [
    ('ManaOrbPommelV2','M_ManaOrbV2_Glass','ManaOrbPommelV2_20261024','M_RuneboundManaOrb_GemV2'),
    ('StarTideCoreV1','M_StarTide_Glass','StarTideCoreV1_20261024','M_RuneboundManaOrb_StarTide_Gem')]:
    source=(FAMILY/folder/'import_assets.py').read_text('utf-8')
    before=ROOT/'Content/Weapons/RuneboundWarhammer20261022'/folder/(name+'.uasset')
    backup=P/'Before'/stamp/folder;backup.mkdir(parents=True,exist_ok=True);shutil.copy2(before,backup/before.name)
    ns={'u':u,'json':json,'P':P,'ROOT':ROOT,'D':'/Game/Weapons/RuneboundWarhammer20261022/'+folder,
        'TAG':'RuneboundManaOrbOwner','OWNER':owner,'receipt':receipt,
        'A':u.AssetToolsHelpers.get_asset_tools(),'E':u.EditorAssetLibrary,'L':u.MaterialEditingLibrary}
    exec(defs,ns)
    ns['record']=record
    base_material=ns['material']
    def make_material(key,base_material=base_material):
        result=base_material(key);result.set_editor_property('used_with_nanite',False);return result
    ns['material']=make_material;ns['materials']={}
    start=source.index("m=material('"+name+"')");end=source.index("\nm=material('"+end_name+"')",start)
    exec(compile(source[start:end],'<colored_crystal_edge>','exec'),ns)
    material=ns['materials'][name]
    stats=u.MaterialEditingLibrary.get_statistics(material)
    receipt['gpu_compilation'][name]={'vertex_instructions':stats.num_vertex_shader_instructions,'pixel_instructions':stats.num_pixel_shader_instructions}
    record()
    if stats.num_pixel_shader_instructions<=0:raise RuntimeError('No compiled pixel shader for '+name)
receipt['complete']=True;record();print('BOTH_ORB_EDGES_COMPILED_AND_SAVED '+json.dumps(receipt['gpu_compilation']))
