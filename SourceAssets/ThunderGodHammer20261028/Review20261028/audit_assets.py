"""Read-only independent UE load of this hammer's saved dependencies."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parent.parents[1]
report=json.loads((P/'catalog-result.json').read_text(encoding='utf-8'))
rows=[];failures=[];seen=set();pending=list(report['asset_references'])
registry=u.AssetRegistryHelpers.get_asset_registry()
opts=u.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True)
def check(label,ok,detail=None):
    row={'check':label,'pass':bool(ok),'detail':detail};rows.append(row)
    if not ok:failures.append(row)
def vec(v):return [v.x,v.y,v.z]
records=[]
while pending:
    ref=pending.pop().split('.')[0]
    if ref in seen:continue
    seen.add(ref);a=u.load_asset(ref);check('load '+ref,a is not None)
    if not a:continue
    info={'asset':ref,'class':a.get_class().get_name()}
    if isinstance(a,u.StaticMesh):
        mats=a.get_editor_property('static_materials');info['materials']=[m.material_interface.get_path_name() if m.material_interface else None for m in mats]
        check('non-default material slots '+ref,bool(mats) and all(m.material_interface and '/Engine/EngineMaterials/DefaultMaterial' not in m.material_interface.get_path_name() for m in mats))
        box=a.get_bounding_box();info['bounds_min']=vec(box.min);info['bounds_max']=vec(box.max)
        if '/ThunderGodHammer20261028/' in ref:
            settings=a.get_editor_property('nanite_settings');info['nanite']=settings.enabled
            if settings.enabled:check('complete fallback '+ref,settings.fallback_percent_triangles==1. and settings.fallback_relative_error==0.)
    if isinstance(a,u.AnimSequence):
        info['duration']=a.get_editor_property('sequence_length');info['skeleton']=str(a.get_editor_property('skeleton'))
        check('playable animation '+ref,info['duration']>0 and a.get_editor_property('skeleton') is not None)
    if '/ThunderGodHammer20261028/' in ref:
        for dep in registry.get_dependencies(ref,opts):
            if str(dep).startswith('/Game/'):pending.append(str(dep))
    records.append(info)
base='/Game/Weapons/ThunderGodHammer20261028'
for suffix,srgb in [('BaseColor',True),('MetallicRoughness',False),('Normal',False)]:
    a=u.load_asset(base+'/Textures/T_ThunderGodHammer_'+suffix)
    check('PBR texture colorspace '+suffix,a is not None and a.get_editor_property('srgb')==srgb)
    if suffix=='Normal' and a:check('glTF normal green channel conversion',a.get_editor_property('flip_green_channel'))
material=u.load_asset(base+'/Materials/M_ThunderGodHammerSurface')
textures=[n.get_editor_property('texture').get_path_name() for n in u.MaterialEditingLibrary.get_material_expressions(material)
          if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture')]
check('saved PBR texture sample references include all three maps',all(any('T_ThunderGodHammer_'+s in t for t in textures) for s in ('BaseColor','MetallicRoughness','Normal')),textures)
rune=u.load_asset(base+'/ModulesV1/Runes/M_SilverRuneSurface_ThunderGodHammerShaftV1')
custom=next(n for n in u.MaterialEditingLibrary.get_material_expressions(rune) if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
code=custom.get_editor_property('code');check('saved rune shader uses target shaft coordinates','float artHeight = 33.5;' in code and 'float shaftStart = -35.5;' in code and 'float2(-.0445214100, .1056659501)' in code)
result={'complete':True,'count':len(rows),'failures':failures,'checks':rows,'assets':records,'packages_saved':False,'game_started':False}
(P/'assets-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('THUNDER_ASSETS_RESULT '+json.dumps({'count':len(rows),'loaded':len(records),'failures':failures}))
if failures:raise RuntimeError('Hammer asset load checks failed')
