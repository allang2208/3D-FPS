"""Read existing asset dependencies only. No worlds, simulations, renders, edits or saves."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,ref,emitters
AR=u.AssetRegistryHelpers.get_asset_registry()
ROOTS=['/Game/NiagaraExamples','/Game/Vefects/Free_Fire','/Game/RPGEnvironmentVFX',
       '/Game/MilitaryTrench/Particles','/Game/EasyBuildingSystem/Effects','/Game/_SplineVFX',
       '/Game/Realistic_Starter_VFX_Pack_Vol2','/NiagaraFluids']
out={'roots':ROOTS,'catalog':[],'candidates':[],'errors':[]}
AR.wait_for_completion()
for root in ROOTS:
    for a in AR.get_assets_by_path(root,True):
        cls=str(a.asset_class_path.asset_name)
        if cls in ('NiagaraSystem','NiagaraEmitter','ParticleSystem','Blueprint'):
            out['catalog'].append({'path':str(a.package_name),'class':cls})
OPTIONS=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,
    include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
def get(obj,key):
    try:return obj.get_editor_property(key)
    except Exception:return None
def path(obj):return obj.get_path_name() if obj else None
def dependencies(package):
    seen=set(); todo=[(package,0)]; result=[]
    while todo:
        p,depth=todo.pop(0)
        if p in seen or p.startswith('/Script/'):continue
        seen.add(p)
        for a in AR.get_assets_by_package_name(p):
            result.append({'path':p,'class':str(a.asset_class_path.asset_name),'depth':depth})
        if depth<4:
            for dep in AR.get_dependencies(p,OPTIONS):
                s=str(dep)
                if not s.startswith('/Engine/') and not s.startswith('/Niagara/') and not s.startswith('/NiagaraFluids/Modules/'):
                    todo.append((s,depth+1))
        if len(seen)>600:break
    return result
def material_info(mat):
    row={'path':path(mat)}
    base=mat.get_base_material()
    row.update(base=path(base),blend=str(get(base,'blend_mode')),shading=str(get(base,'shading_model')),
        refraction=str(get(base,'refraction_method')))
    if isinstance(mat,u.MaterialInstanceConstant):
        row['scalars']={str(n):LIB.get_material_instance_scalar_parameter_value(mat,n) for n in LIB.get_scalar_parameter_names(mat)}
        row['textures']={str(n):path(LIB.get_material_instance_texture_parameter_value(mat,n)) for n in LIB.get_texture_parameter_names(mat)}
        row['vectors']={str(n):str(LIB.get_material_instance_vector_parameter_value(mat,n)) for n in LIB.get_vector_parameter_names(mat)}
    row['inputs']={str(k):path(LIB.get_material_property_input_node(base,k)) for k in
        (u.MaterialProperty.MP_EMISSIVE_COLOR,u.MaterialProperty.MP_OPACITY,u.MaterialProperty.MP_REFRACTION)}
    row['texture_nodes']=[]
    for node in LIB.get_material_expressions(base):
        texture=get(node,'texture')
        if texture:
            row['texture_nodes'].append({'class':node.get_class().get_name(),'texture':path(texture)})
    return row
def inspect(p):
    a=u.load_asset(p)
    if not a:return {'path':p,'missing':True}
    row={'path':p,'class':a.get_class().get_name(),'dependencies':dependencies(p)}
    if isinstance(a,u.NiagaraSystem):
        row['emitters']=[]
        for name in emitters(a):
            top=API.call_method('GetEmitterTopology',(ref(a,name),))
            e={'name':name,'modules':{},'renderers':[]}
            for phase in ('emitter_update_script','particle_spawn_script','particle_update_script'):
                e['modules'][phase]=[str(m.get_editor_property('module_name')) for m in top.get_editor_property(phase).get_editor_property('modules')]
            for index in range(3):
                try:
                    raw=API.call_method('GetRendererData',(ref(a,name,renderer=index),)).get_editor_property('property_values')
                    if raw and raw!='{}':
                        data=json.loads(raw)
                        keep=('Material','SubImageSize','bSubImageBlend','Meshes','FacingMode','Alignment','RendererEnabledBinding')
                        e['renderers'].append({key:value for key,value in data.items() if key in keep})
                    else:break
                except Exception:break
            row['emitters'].append(e)
    elif isinstance(a,u.ParticleSystem):
        dest=ROOT/'SourceAssets/Campfire20261012/InventoryExports'
        dest.mkdir(exist_ok=True)
        task=u.AssetExportTask();task.object=a;task.filename=str(dest/(a.get_name()+'.t3d'))
        task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False;task.replace_identical=True
        row['text_export']={'file':task.filename,'success':u.Exporter.run_asset_export_task(task)}
        row['emitters']=[]
        for emitter in get(a,'emitters') or []:
            e={'class':emitter.get_class().get_name(),'name':str(get(emitter,'emitter_name')),'lods':[]}
            for lod in get(emitter,'lod_levels') or []:
                required=get(lod,'required_module')
                e['lods'].append({'material':path(get(required,'material')),
                    'subimages_x':get(required,'sub_images_horizontal'),'subimages_y':get(required,'sub_images_vertical'),
                    'modules':[m.get_class().get_name() for m in get(lod,'modules') or []]})
            row['emitters'].append(e)
    row['materials']=[];row['textures']=[]
    for d in row['dependencies']:
        try:
            if d['class'] in ('Material','MaterialInstanceConstant'):
                row['materials'].append(material_info(u.load_asset(d['path'])))
            elif d['class']=='Texture2D':
                t=u.load_asset(d['path'])
                row['textures'].append({'path':d['path'],'width':t.blueprint_get_size_x(),'height':t.blueprint_get_size_y(),
                    'compression':str(get(t,'compression_settings')),'srgb':get(t,'srgb')})
        except Exception as exc:out['errors'].append(d['path']+': '+str(exc))
    return row
CANDIDATES=['/Game/NiagaraExamples/FX_Misc/NS_Fire','/Game/Vefects/Free_Fire/Shared/Particles/BP_Fire',
    '/Game/Vefects/Free_Fire/Shared/Particles/NS_Fire_Medium','/Game/Vefects/Free_Fire/Shared/Particles/NS_Fire_Small',
    '/Game/MilitaryTrench/Particles/P_Fire','/Game/EasyBuildingSystem/Effects/PS_CampFire',
    '/Game/_SplineVFX/NS/NS_Spline_Fire','/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Fire/P_flamethrower',
    '/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Fire/P_Fire_Small',
    '/NiagaraFluids/Templates/Gas/3D/Systems/Grid3D_Gas_Fire']
for p in CANDIDATES:
    try:out['candidates'].append(inspect(p))
    except Exception as exc:out['errors'].append(p+': '+str(exc))
    (ROOT/'SourceAssets/Campfire20261012/local-fire-inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('CAMPFIRE_LOCAL_FIRE_INVENTORY',len(out['catalog']),len(out['candidates']),len(out['errors']))
