"""Polish only Time Sand mode 7 on the current rune-sword masters."""
# Apply the shared workbench copy standard when publishing catalogs.
from pathlib import Path as _WorkbenchCopyPath
import runpy as _workbench_copy_runpy
_workbench_copy_root = next(p for p in _WorkbenchCopyPath(__file__).resolve().parents if (p / 'FPSGAME.uproject').exists())
_apply_workbench_copy = _workbench_copy_runpy.run_path(str(_workbench_copy_root / 'SourceAssets/WorkbenchCopy20261101/copy_rules.py'))['apply_for_target']

from pathlib import Path
import json, shutil
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;REV='TimeSandPolish20261101V2'
MASTERS=['/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
 '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold']
if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('PIE is running; preserve the current session.')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name() in MASTERS:raise RuntimeError('Unsaved target package '+package.get_path_name())

def node(m,cls,**props):
    result=L.create_material_expression(m,cls)
    for key,value in props.items():result.set_editor_property(key,value)
    return result
def wire(src,dst,pin,channel=''):
    names=[str(n) for n in L.get_material_expression_input_names(dst)]
    norm=lambda s:s.replace(' ','').replace('_','').lower()
    actual=next((n for n in names if norm(n)==norm(pin)),None)
    if actual is None and pin=='Input' and len(names)==1:actual=names[0]
    if actual is None or not L.connect_material_expressions(src,channel,dst,actual):raise RuntimeError('Material pin '+pin+' '+str(names))
def custom(m,label,code,width,inputs):
    result=node(m,u.MaterialExpressionCustom,desc=REV+' '+label,code=code,
                output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    result.set_editor_property('inputs',pins)
    for name,(src,channel) in inputs.items():wire(src,result,name,channel)
    return result
def input_source(m,expression,name):
    for pin,src in zip(L.get_material_expression_input_names(expression),L.get_inputs_for_material_expression(m,expression)):
        if str(pin)==name and src:return src,str(L.get_input_node_output_name_for_material_expression(expression,src))
    raise RuntimeError('Existing input missing '+name)
def add_input(expression,name,src,channel=''):
    pins=list(expression.get_editor_property('inputs'))
    pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    expression.set_editor_property('inputs',pins);wire(src,expression,name,channel)
def replace_branch(code,recipe):
    start=code.index('// TimeSandMaterial20261101V1');opening=code.index('{',start);end=opening+1;depth=1
    while depth:
        depth+=(code[end]=='{')-(code[end]=='}');end+=1
    return code[:start]+'// '+REV+'\nif(Mode>6.5 && Mode<7.5){\n'+recipe+'\n}\n'+code[end:]

# Real metallic reflection supplies the gloss. Sand changes reflectance/roughness
# in sparse sub-millimeter flecks, without painted highlight stripes or emission.
SAND='''float w=1-saturate(Mask*3.0);
float2 q=float2(P.x*12+sin(P.z*.055)*.8,P.z*9-TimeSandTime*1.3);
float2 cell=floor(q),f=frac(q)-.5;
float seed=frac(sin(dot(cell,float2(127.1,311.7)))*43758.5453);
float footprint=max(length(ddx(q)),length(ddy(q)));
float filtered=exp2(-.55*footprint*footprint);
float pulse=.75+.25*sin(TimeSandTime*.8+seed*6.283185);
float sand=exp(-dot(f,f)*78)*step(.88,seed)*pulse*filtered;
float cloud=sin(P.x*.39+P.z*.071)*sin(P.z*.113-P.x*.17);
'''
RECIPES={
 'MP_BASE_COLOR':SAND+'''float3 gold=float3(.74,.49,.22)*(1+cloud*.022);
gold=lerp(gold,float3(.91,.72,.42),Edge*.65);
gold+=float3(.14,.11,.055)*sand;
return lerp(Base,min(gold,float3(.98,.98,.98)),w);''',
 'MP_ROUGHNESS':SAND+'''float polishPhase=P.x*320+sin(P.z*1.8)*.3;
float pw=fwidth(polishPhase);
float polish=sin(polishPhase)*exp2(-.45*pw*pw);
float rough=.195+cloud*.012+polish*.004-sand*.055;
return lerp(Base,lerp(clamp(rough,.135,.23),.11,Edge),w);''',
 'MP_NORMAL':'return Base;',
 'MP_METALLIC':'return lerp(Base,.98,1-saturate(Mask*3.0));'}

saved=[]
for path in MASTERS:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing current master '+path)
    if E.get_metadata_tag(mat,'TimeSandPolishRevision')==REV:
        saved.append({'asset':path,'already_current':True});continue
    source=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=P/'BeforeAssets'/source.relative_to(ROOT/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
    expressions=L.get_material_expressions(mat)
    finishes=[n for n in expressions if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc')).startswith('BladeFinish20261031V1 ')]
    if len(finishes)!=4:raise RuntimeError('Current finish graph missing '+path)
    color=next(n for n in finishes if 'MP_BASE_COLOR:' in str(n.get_editor_property('desc')))
    edge=input_source(mat,color,'Edge')[0]
    local_normal=input_source(mat,edge,'N')
    for field,recipe in RECIPES.items():
        finish=next(n for n in finishes if field+':' in str(n.get_editor_property('desc')))
        finish.set_editor_property('code',replace_branch(str(finish.get_editor_property('code')),recipe))
    # Extend the existing reflection outputs only for mode 7; other finishes keep
    # their existing direction and amount, including Meteoric Iron V2.
    anisotropy=next(n for n in expressions if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='MeteoricIron20261101V2 ANISOTROPY')
    anisotropy.set_editor_property('code','// '+REV+'\nif(Mode>6.5 && Mode<7.5)return lerp(Base,.38*(1-.65*Edge),1-saturate(Mask*3.0));\n'+str(anisotropy.get_editor_property('code')))
    tangent=next(n for n in expressions if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='MeteoricIron20261101V2 TANGENT')
    direction=custom(mat,'longitudinal fine polish','float3 n=normalize(N);float3 axis=abs(n.z)<.9?float3(0,0,1):float3(1,0,0);return normalize(axis-n*dot(axis,n));',3,{'N':local_normal})
    transform=node(mat,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT if mat.get_editor_property('tangent_space_normal') else u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(direction,transform,'Input');add_input(tangent,'TimeSandBrush',transform)
    tangent.set_editor_property('code','// '+REV+'\nif(Mode>6.5 && Mode<7.5)return normalize(lerp(Base,TimeSandBrush,1-saturate(Mask*3.0)));\n'+str(tangent.get_editor_property('code')))
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Time Sand shader compilation failed '+str(errors))
    E.set_metadata_tag(mat,'TimeSandPolishRevision',REV)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Material save failed '+path)
    saved.append({'asset':path,'saved':True,'mode':7,'compile_errors':list(errors)})

appearance='符文长剑专属。香槟金剑面泛起细腻拉丝亮泽，精抛刃缘清亮，细砂在金属深处缓缓流动。'
for filename in ['melee-gunsmith.json','rune-sword-modules.json']:
    path=ROOT/'Content/ColdSteelData'/filename;before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
    if filename=='melee-gunsmith.json':
        options=next(c for c in data['columns'] if c['key']=='blade_material')['options']
        next(o for o in options if o['id']=='time_sand_gold')['description']=appearance
    else:data['slots']['blade_material']['time_sand_gold']['appearance']=appearance
    backup=P/'BeforeCatalog'/filename;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Catalog changed during merge '+filename)
    path.write_text(json.dumps(_apply_workbench_copy(path, data),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(P/'material-receipt.json').write_text(json.dumps(_apply_workbench_copy(P/'material-receipt.json', {'revision':REV,'materials':saved,
    'gameplay_tested':False,'preview_rendered':False}),indent=2)+'\n',encoding='utf8')
print('TIME_SAND_POLISH_SAVED',json.dumps(saved))
