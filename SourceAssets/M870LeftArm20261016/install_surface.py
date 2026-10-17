"""Persist the local elbow corrective to M870-only viewmodel surfaces."""
import json,itertools,shutil
from pathlib import Path
import unreal as u
SOURCE='/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_BareArmsV7'
BARE='/Game/Weapons/M870/Arms20261016/SK_M870_BareArmsV7'
WEAPON='/Game/Weapons/M870/Tactical20261015/SK_M870_V7'
TAG='M870LeftElbowSurface'

def apply_surface(O,P,report):
    patch=json.loads((O/'elbow_surface.json').read_text());edits=patch['coordinate_edits'];library=u.EditorAssetLibrary
    config=P/'Content/ColdSteelData/modular_outfits.json';c=json.loads(config.read_text(encoding='utf-8'));key=WEAPON+'.SK_M870_V7'
    expected=SOURCE+'.SK_Super90_BareArmsV7';replacement=BARE+'.SK_M870_BareArmsV7'
    for field in ('base','native_bare_skin','bare_arms_candidate'):
        if c['profiles'][key][field] not in (expected,replacement):raise RuntimeError('M870 outfit profile changed; preserve '+field)
    source=library.load_asset(SOURCE)
    target=library.load_asset(BARE) if library.does_asset_exist(BARE) else library.duplicate_asset(SOURCE,BARE)
    if not source or not target:raise RuntimeError('Cannot prepare the dedicated M870 bare surface')
    G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
    def native(p):return (100*p[0],-100*p[1],100*p[2])
    def cell(p):return tuple(round(x/.01) for x in p)
    buckets={}
    for index,e in enumerate(edits):buckets.setdefault(cell(native(e['before'])),[]).append((index,e))
    prepared=[]
    for path in (WEAPON,BARE):
        asset=library.load_asset(path)
        if library.get_metadata_tag(asset,TAG)=='20261016':
            report.setdefault('surfaces',{})[path]={'saved':True,'already_installed':True,'revision':'20261016'}
            continue
        dm,result=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
        _,positions,_=Q.get_all_vertex_positions(dm,False);positions=u.GeometryScript_List.convert_vector_list_to_array(positions);changes=[];found=set()
        for i,p in enumerate(positions):
            point=(p.x,p.y,p.z);k=cell(point);near=[]
            for delta in itertools.product((-1,0,1),repeat=3):near.extend(buckets.get(tuple(k[j]+delta[j] for j in range(3)),()))
            for idx,e in near:
                before=native(e['before'])
                if sum((point[j]-before[j])**2 for j in range(3))<.000025:
                    changes.append((i,native(e['after'])));found.add(idx);break
        if len(found)!=len(edits):raise RuntimeError('Elbow source mismatch '+path+': '+str(len(found))+'/'+str(len(edits)))
        prepared.append((path,asset,dm,changes))
    for path,asset,dm,changes in prepared:
        physical=P/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=O/'Before'/(path.removeprefix('/Game/')+'.uasset')
        if physical.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(physical,backup)
        for index,point in changes:
            _,valid=u.GeometryScript_MeshEdits.set_vertex_position(dm,index,u.Vector(*point),True)
            if not valid:raise RuntimeError('Cannot write elbow vertex '+path)
        _,selection=u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(dm,[i for i,_ in changes],u.GeometryScriptMeshSelectionType.VERTICES)
        u.GeometryScript_Normals.recompute_normals_for_mesh_selection(dm,selection,u.GeometryScriptCalculateNormalsOptions())
        options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=False,enable_recompute_normals=False,enable_recompute_tangents=False,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,result=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
        if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot persist '+path)
        subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);count=subsystem.get_lod_count(asset)
        if count>1 and not subsystem.regenerate_lod(asset,count,True,False):raise RuntimeError('Cannot rebuild existing LODs '+path)
        library.set_metadata_tag(asset,TAG,'20261016')
        if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Cannot save '+path)
        report.setdefault('surfaces',{})[path]={'vertices':len(changes),'max_displacement_mm':patch['max_displacement_mm'],'saved':True}
        (O/'install_receipt.json').write_text(json.dumps(report,indent=2))
    backup=O/'Before/modular_outfits.json';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(config,backup)
    # Merge only this weapon's three bare-surface paths after the new asset saved.
    c=json.loads(config.read_text(encoding='utf-8'))
    for field in ('base','native_bare_skin','bare_arms_candidate'):
        if c['profiles'][key][field] not in (expected,replacement):raise RuntimeError('M870 outfit profile changed before save')
        c['profiles'][key][field]=replacement
    config.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report['outfit_profile_saved']=str(config);report['shared_super90_mesh_modified']=False
