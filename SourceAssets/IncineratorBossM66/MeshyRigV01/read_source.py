import bpy, json, hashlib, shutil
from pathlib import Path
from mathutils import Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/MeshyRigV01')
SOURCE=Path('C:/Users/allan/Downloads/Meshy_AI_Character_output (3).glb')
for name in ['Inputs','Records','Authoring','Export','Textures']:(ROOT/name).mkdir(parents=True,exist_ok=True)
copy=ROOT/'Inputs/M66_user_rig.glb'
if not copy.exists():shutil.copy2(SOURCE,copy)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(copy))
report={'source':str(SOURCE),'sha256':hashlib.sha256(copy.read_bytes()).hexdigest(),'objects':[],'armatures':[],'actions':[]}
for obj in bpy.context.scene.objects:
    if obj.type=='ARMATURE':
        report['armatures'].append({'name':obj.name,'matrix':[list(r) for r in obj.matrix_world],
            'bones':[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(obj.matrix_world@b.head_local),'tail':list(obj.matrix_world@b.tail_local),'deform':b.use_deform} for b in obj.data.bones]})
    if obj.type=='MESH':
        positions=[obj.matrix_world@v.co for v in obj.data.vertices]
        missing=[];totals={g.name:{'vertices':0,'weight':0.0,'center':[0.0]*3} for g in obj.vertex_groups}
        for v,p in zip(obj.data.vertices,positions):
            if sum(g.weight for g in v.groups)<.00001:missing.append(v.index)
            for g in v.groups:
                if g.weight<=0:continue
                row=totals[obj.vertex_groups[g.group].name];row['vertices']+=1;row['weight']+=g.weight
                for k in range(3):row['center'][k]+=p[k]*g.weight
        for row in totals.values():
            if row['weight']:row['center']=[x/row['weight'] for x in row['center']]
        report['objects'].append({'name':obj.name,'vertices':len(positions),'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),
            'bounds':[[min(p[k] for p in positions) for k in range(3)],[max(p[k] for p in positions) for k in range(3)]],
            'missing_count':len(missing),'missing_indices':missing,'weights':totals,
            'materials':[m.name for m in obj.data.materials], 'modifiers':[{'name':m.name,'type':m.type} for m in obj.modifiers]})
for a in bpy.data.actions:report['actions'].append({'name':a.name,'frames':list(a.frame_range)})
report['images']=[{'name':i.name,'size':list(i.size),'format':i.file_format,'path':i.filepath} for i in bpy.data.images]
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/M66_source.blend'))
(ROOT/'Records/source_structure.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_SOURCE '+json.dumps({k:v for k,v in report.items() if k not in ['objects','armatures','images']}))
for obj in report['objects']:print('M66_MESH '+json.dumps({k:v for k,v in obj.items() if k not in ['weights','missing_indices']}))
for arm in report['armatures']:
    for b in arm['bones']:print('M66_BONE '+json.dumps(b))
