"""Requested read-only audit of the saved tactical-belt delivery."""
import json,hashlib,gc
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/TacticalMagazineBelt20261024';O=R/'Review20261024';O.mkdir(exist_ok=True)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
saved=read(R/'saved_assets.json');delivery=read(R/'delivery.json');catalog=read(P/'Content/ColdSteelData/items.json');cfg=read(P/'Content/ColdSteelData/modular_outfits.json');key='ue_tactical_magazine_belt'
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem);SS=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
rows=[];checks=[]
def check(name,ok,detail=''):checks.append(dict(name=name,passed=bool(ok),detail=detail))
for body in ('Jason','Kaitlin'):
    profile=cfg if body=='Jason' else cfg['body_variants']['kaitlin'];recipe=profile['items'][key]
    check(body+' configured world and owner',recipe['rig_meshes'][body]==saved['wear'][body]['asset']==recipe['owner_body_meshes'][body])
    source=next(r for r in delivery['records'] if r['body']==body)
    for kind,field in [('wear','lods'),('wear_empty','empty_lods')]:
        path=saved[kind][body]['asset'];mesh=u.load_asset(path);check(path+' load',mesh is not None)
        if not mesh:continue
        check(path+' LOD count',S.get_lod_count(mesh)==3);counts=[]
        native=u.load_asset(source['source']);check(path+' native skeleton',mesh.skeleton==native.skeleton)
        for lod,src in enumerate(source[field]):
            dm,outcome=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_index=lod))
            count=dm.get_triangle_count();counts.append(count);check(path+' LOD '+str(lod),outcome==u.GeometryScriptOutcomePins.SUCCESS and count==src['triangles'],dict(saved=count,authored=src['triangles']))
            del dm;gc.collect()
        materials=list(mesh.get_editor_property('materials'));check(path+' material slots',len(materials)==10 and all(x.material_interface for x in materials))
        rows.append(dict(path=path,triangles=counts,skeleton=mesh.skeleton.get_path_name()))
for kind in ('pickup','icon'):
    path=saved[kind]['asset'];asset=u.load_asset(path);check(kind+' loads',asset is not None)
    if asset:
        check(kind+' LOD count',SS.get_lod_count(asset)==saved[kind]['lod_count']);rows.append(dict(path=path,lods=SS.get_lod_count(asset)))
for kind,row in saved['magazines'].items():
    asset=u.load_asset(row['asset']);check(kind+' magazine loads',asset is not None and SS.get_lod_count(asset)==3)
for path in saved['materials']+list(saved['textures'].values())+[saved['icon_texture']]:check(path,u.load_asset(path) is not None)
icon=P/'Content/ColdSteelData'/catalog[key]['ue_icon'];check('inventory PNG',icon.exists() and hashlib.sha256(icon.read_bytes()).hexdigest()==saved['icon_sha256'])
check('belt slot and grid',catalog[key]['equipSlot']=='belt' and catalog[key]['grid_w']==2 and catalog[key]['grid_h']==1)
check('pickup catalog',catalog[key]['world_mesh']==saved['pickup']['asset'])
report=dict(passed=all(x['passed'] for x in checks),checks=checks,meshes=rows,read_only=True,rendered=False)
(O/'assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('BELT_ASSET_REVIEW',report['passed'],'checks',len(checks),'failures',[x for x in checks if not x['passed']],flush=True)
