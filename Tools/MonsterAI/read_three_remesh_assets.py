"""Read only the three requested live meshes, LODs, materials and death bindings."""
from pathlib import Path
from datetime import datetime
import unreal as u
import json,re,traceback
P=Path('D:/FPS3D/FPSGAME');OUT=P/'SourceAssets/AlienGeometry20261006/AnatomyInspection20261007'
OUT.mkdir(parents=True,exist_ok=True)
ids=('M10Mawcrawler','HangingBellM09','LurkerM08')
report=dict(started=datetime.now().isoformat(),complete=False,assets_saved=False,gameplay_run=False,actors=[],meshes={},errors=[])
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);R=u.AssetRegistryHelpers.get_asset_registry()
def write():(OUT/'runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf8')
def prop(obj,key,default=None):
    try:return obj.get_editor_property(key)
    except Exception:return default
def path(obj):return obj.get_path_name() if obj else None
def mesh_info(mesh):
    key=path(mesh)
    if key in report['meshes']:return key
    data=u.AssetRegistryHelpers.create_asset_data(mesh);entry=dict(path=key,lods=[],materials=[],tags={})
    for name in ('Triangles','Vertices','Bones','MorphTargets','MaxBoneInfluences'):entry['tags'][name]=u.AssetRegistryHelpers.get_tag_value(data,name)
    for level in range(S.get_lod_count(mesh)):
        dynamic=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.set_editor_property('lod_type',u.GeometryScriptLODType.RENDER_DATA);lod.set_editor_property('lod_index',level)
        _,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,dynamic,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
        if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+key+' LOD '+str(level))
        entry['lods'].append(dict(level=level,triangles=dynamic.get_triangle_count(),vertices=S.get_num_verts(mesh,level),sections=S.get_num_sections(mesh,level)))
        dynamic.reset()
    for slot in mesh.get_editor_property('materials'):
        entry['materials'].append(dict(slot=str(slot.get_editor_property('material_slot_name')),imported=str(slot.get_editor_property('imported_material_slot_name')),asset=path(slot.get_editor_property('material_interface'))))
    entry['skeleton']=path(mesh.get_editor_property('skeleton'))
    entry['import_sources']=list(mesh.get_editor_property('asset_import_data').extract_filenames())
    options=u.AssetRegistryDependencyOptions();options.include_hard_package_references=True;options.include_soft_package_references=False
    deps=R.get_dependencies(key.split('.')[0],options)
    entry['soft_corpse_data_dependencies']=[str(x) for x in deps if '/DA_' in str(x) and 'SoftCorpse' in str(x)]
    entry['binding_present']=any(x and x.get_class().get_name()=='MonsterSoftCorpseBinding' for x in mesh.get_editor_property('asset_user_data'))
    report['meshes'][key]=entry;return key

report['dirty_before']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
source=(P/'Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp').read_text(encoding='utf8')
entries=re.findall(r'Add\(TEXT\("([^"]+)"\),\s*TEXT\("([^"]+)"\),\s*TEXT\("([^"]+)"\)',source)
for ident,label,cls_path in entries:
    if ident not in ids:continue
    try:
        cls=u.load_class(None,cls_path);cdo=u.get_default_object(cls);component=prop(cdo,'mesh')
        mesh=prop(cdo,'visual_mesh') or (component.get_skeletal_mesh_asset() if component else None)
        if not mesh:raise RuntimeError('No active mesh for '+ident)
        key=mesh_info(mesh);item=dict(species=ident,class_path=cls_path,live_mesh=key,corpse_meshes=[])
        for data_path in report['meshes'][key]['soft_corpse_data_dependencies']:
            data=u.load_asset(data_path);corpse=data.get_editor_property('corpse_mesh')
            item['corpse_meshes'].append(mesh_info(corpse))
        report['actors'].append(item);print('ANATOMY_UE_READ '+ident+' '+json.dumps(report['meshes'][key]['lods']),flush=True)
    except Exception:report['errors'].append(dict(species=ident,error=traceback.format_exc()))
    write()
report['dirty_after']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
report['complete']=len(report['actors'])==3 and not report['errors'];write()
if report['errors']:raise RuntimeError(str(report['errors']))
