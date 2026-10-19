"""Read real saved render LODs and current cloth links without saving assets."""
import json,gc,math
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageSetAudit20261019';E=u.EditorAssetLibrary;S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
cfg=read(P/'Content/ColdSteelData/modular_outfits.json');body=read(P/'Content/ColdSteelData/player_body.json');items=read(P/'Content/ColdSteelData/items.json');targets={};report=dict(meshes={},icons={},failures=[])
def add(path,label):
    if path:targets.setdefault(path,[]).append(label)
for key in ('ue_blue_mage_robe','ue_blue_mage_gloves','ue_blue_mage_pants','ue_blue_mage_boots'):
    recipe=cfg['items'][key]
    for rig,path in recipe['rig_meshes'].items():add(path,key+'/'+rig)
    for rig,path in recipe.get('owner_body_meshes',{}).items():add(path,key+'/'+rig+'_Owner')
    for shoe,rigs in recipe.get('shoe_fit_meshes',{}).items():
        for rig,path in rigs.items():add(path,key+'/'+shoe+'/'+rig)
for path,replacement in cfg['items']['ue_blue_mage_robe']['underlayer_meshes'].items():
    add(replacement,'robe_underlayer')
add(body['head_equipment']['ue_blue_mage_hat']['skeletal_mesh'],'ue_blue_mage_hat')
for path,labels in targets.items():
    mesh=u.load_asset(path)
    if not mesh:report['failures'].append('Missing '+path);continue
    row=dict(labels=labels,lod_count=S.get_lod_count(mesh),materials=[m.material_interface.get_path_name() if m.material_interface else None for m in mesh.materials],render_lods=[])
    for i in range(row['lod_count']):
        dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=i))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:report['failures'].append('Cannot read '+path+':'+str(i));continue
        _,vectors,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False);points=u.GeometryScript_List.convert_vector_list_to_array(vectors)
        bounds=[[min(getattr(p,a) for p in points),max(getattr(p,a) for p in points)] for a in ('x','y','z')] if points else []
        finite=bool(points) and all(math.isfinite(value) for p in points for value in (p.x,p.y,p.z))
        row['render_lods'].append(dict(lod=i,vertices=len(points),triangles=dm.get_triangle_count(),bounds=bounds,finite=finite))
        if not finite or dm.get_triangle_count()==0:report['failures'].append('Invalid saved render LOD '+path+':'+str(i))
        del points,vectors,dm
    if row['lod_count']!=3 or None in row['materials']:report['failures'].append('LOD/material contract '+path)
    cloths=mesh.get_editor_property('mesh_clothing_assets');row['cloth_assets']=[]
    for cloth in cloths:
        shared=next((c for c in cloth.get_editor_property('cloth_configs').values() if c.get_class().get_name()=='ChaosClothSharedSimConfig'),None);physics=cloth.get_editor_property('physics_asset')
        row['cloth_assets'].append(dict(path=cloth.get_path_name(),physics=physics.get_path_name() if physics else None,substeps=int(shared.get_editor_property('SubdivisionCount')) if shared else None))
    if '/MovementFit20261019/' in path and (len(cloths)!=1 or row['cloth_assets'][0]['substeps']!=4 or not row['cloth_assets'][0]['physics']):report['failures'].append('Cloth binding '+path)
    report['meshes'][path]=row
    (R/'saved-render-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('MAGE_SAVED_LODS_READ',path.rsplit('/',1)[-1],row['lod_count'],flush=True);del mesh,cloths;gc.collect();u.SystemLibrary.collect_garbage()
for label,family in [('robe','BlueMageRobe20261018'),('hat','BlueMageHat20261019'),('gloves','BlueMageGloves20261019'),('pants','BlueMagePants20261019'),('boots','BlueMageBoots20261019')]:
    saved=read(P/'SourceAssets'/family/'saved_assets.json');key='ue_blue_mage_'+label;tex=u.load_asset(saved['icon_texture']);display=u.load_asset(items[key]['ue_equipment_icon_mesh']);pickup=u.load_asset(items[key]['world_mesh'])
    report['icons'][key]=dict(texture=bool(tex),display=bool(display),pickup=bool(pickup),srgb=bool(tex.get_editor_property('srgb')) if tex else None,lod_group=str(tex.get_editor_property('lod_group')) if tex else None)
    if not tex or not display or not pickup:report['failures'].append('UI/drop assets '+key)
report['completed']=True;report['passed']=not report['failures'];(R/'saved-render-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('MAGE_SAVED_ASSET_AUDIT',report['passed'],len(report['meshes']),flush=True)
