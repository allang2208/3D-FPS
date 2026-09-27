"""Read saved UE geometry and compressed animation poses for the requested glove check.
No assets, maps or gameplay settings are changed.
"""
import json, math
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME')
ROOT=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
OUT=ROOT/globals().get('REVIEW_DIRECTORY','ClearanceReview');OUT.mkdir(exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;G=u.GeometryScript_AssetUtils
def xyz(v):return [v.x,v.y,v.z]
def read_mesh(path,key,lod=0,part=None):
    dest=OUT/(key+'.json')
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing '+path)
    lodspec=u.GeometryScriptMeshReadLOD();lodspec.set_editor_property('lod_index',lod)
    dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),lodspec)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+path)
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,pos,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(pos)
    _,tri,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(tri)
    weights=[]
    for i in range(len(ps)):
        _,ws,ok=B.get_vertex_bone_weights(dm,i)
        if not ok:raise RuntimeError('Missing weights '+key)
        weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
    d=dict(path=path,lod=lod,positions=[xyz(v) for v in ps],triangles=[xyz(t) for t in ts],weights=weights,
        triangle_materials=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(ts))],
        bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),
            axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
    if part:
        slots=asset.get_editor_property('materials')
        leather=next(i for i,m in enumerate(slots) if str(m.material_slot_name)=='FingerlessGloveLeather')
        faces=[i for i,m in enumerate(d['triangle_materials']) if (m==leather)==(part=='glove')]
        used=sorted({v for i in faces for v in d['triangles'][i]});remap={v:i for i,v in enumerate(used)}
        d['positions']=[d['positions'][i] for i in used];d['weights']=[d['weights'][i] for i in used]
        d['triangles']=[[remap[v] for v in d['triangles'][i]] for i in faces];d['triangle_materials']=[d['triangle_materials'][i] for i in faces]
    dest.write_text(json.dumps(d,separators=(',',':')))
    print('CLEARANCE_MESH',key,len(ps),len(ts),flush=True)
    return d

profiles={}
for path,p in cfg['profiles'].items():profiles[p['rig_profile']]=(path,p)
manifest=[]
for name,(path,p) in profiles.items():
    glove=cfg['items']['ue_field_gloves']['rig_meshes'][name]
    skin=p['native_bare_skin']
    combined=False
    if globals().get('READ_COMPANIONS',False):
        skin=json.loads((ROOT/'SkinCoverage/asset-receipt.json').read_text())['profiles'][name]
        combined=any(str(m.material_slot_name)=='FingerlessGloveLeather' for m in u.load_asset(skin).get_editor_property('materials'))
        if combined:glove=skin
    for kind,source in [('skin',skin),('glove',glove)]:
        read_mesh(source,name+'_'+kind,part=kind if combined else None)
    manifest.append(dict(profile=name,source=path,skin=skin,glove=glove))
    if name in ('M4','PKM','A762'):
        for lod in (1,2):
            for kind,source in [('skin',skin),('glove',glove)]:read_mesh(source,f'{name}_{kind}_lod{lod}',lod,kind if combined else None)
        sleeve=cfg['items']['ue_field_gloves'].get('sleeve_meshes',{}).get(name,cfg['items']['ue_field_sweater']['rig_meshes'][name]) if globals().get('READ_COMPANIONS',False) else cfg['items']['ue_field_sweater']['rig_meshes'][name]
        read_mesh(sleeve,name+'_shirt')
(OUT/'mesh-manifest.json').write_text(json.dumps(manifest,indent=2))

clips=[]
states=('idle','aim','fire','aim_fire','reload','reload_empty')
for name,folder,prefix in [('PKM','PKMLowpoly20260922/Animations','A_PKM_'),('A762','A762/Integrated20260920/Animations','A_A762_')]:
    for state in states:clips.append((name,'base_'+state,'/Game/Weapons/'+folder+'/'+prefix+state))
for state in states:
    if state=='reload':path='/Game/Weapons/M4TacticalTossFinal/A_M4_HK416_reload'
    elif state=='reload_empty':path='/Game/Weapons/M4SlapImpactFinal/A_M4_HK416_reload_empty'
    else:path='/Game/Weapons/M4ContactImpactFinal/A_AKM_'+state
    clips.append(('M4','base_'+state,path))
for name,folder in [('PKM','PKMLowpoly20260922/Accessories14'),('A762','A762/Accessories05')]:
    for f in sorted((P/'Content/Weapons'/folder/'Animations').glob('*/*.uasset')):
        if any(f.stem.endswith('_'+s) for s in states):
            clips.append((name,f.parent.name+'_'+f.stem,'/Game/'+f.relative_to(P/'Content').with_suffix('').as_posix()))
results=[]
if globals().get('MESHES_ONLY',False):clips=[]
for name,label,path in clips:
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing clip '+path)
    mesh=u.load_asset(profiles[name][0]);d=json.loads((OUT/(name+'_skin.json')).read_text())
    opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED;opts.optional_skeletal_mesh=mesh
    duration=asset.get_editor_property('sequence_length')
    samples=max(3,min(121,math.ceil(duration*15)+1)) if 'reload' in label else 7
    times=[duration*i/(samples-1) for i in range(samples)]
    poses=[]
    for t in times:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,opts)
        world={}
        for n in d['bones']:
            tr=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)
            world[n]=dict(position=xyz(tr.translation),axes=[xyz(tr.transform_location(v)-tr.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))])
        poses.append(dict(time=t,bones=world))
    row=dict(profile=name,label=label,asset=path,duration=duration,poses=poses)
    (OUT/(name+'__'+label+'_poses.json')).write_text(json.dumps(row,separators=(',',':')))
    results.append(dict(profile=name,label=label,asset=path,samples=samples))
    print('CLEARANCE_POSES',name,label,samples,flush=True)
(OUT/'pose-manifest.json').write_text(json.dumps(results,indent=2))
print('CLEARANCE_READ_COMPLETE',len(manifest),len(results),flush=True)
