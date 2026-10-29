"""Read the two supplied attack FBXs without changing their content."""
import bpy, json
from pathlib import Path

OUT=Path(__file__).resolve().parent
result={}
for path in sorted((OUT/'Original/Animations').glob('*Attack*.fbx')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
    entry={'objects':[], 'actions':[]}
    for obj in bpy.data.objects:
        row={'name':obj.name,'type':obj.type}
        if obj.type=='ARMATURE':
            row['bones']=[b.name for b in obj.data.bones]
            row['parents']=[b.parent.name if b.parent else None for b in obj.data.bones]
        if obj.type=='MESH':row['vertices']=len(obj.data.vertices)
        entry['objects'].append(row)
    for action in bpy.data.actions:
        row={'name':action.name,'frames':list(action.frame_range),'slots':[s.identifier for s in action.slots]}
        curves=[]
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag=strip.channelbag(slot)
                    if bag:
                        for fc in bag.fcurves:
                            vals=[float(p.co.y) for p in fc.keyframe_points]
                            curves.append({'path':fc.data_path,'index':fc.array_index,'keys':len(vals),'range':[min(vals),max(vals)]})
        row['curves']=curves
        entry['actions'].append(row)
    entry['fps']=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    result[path.name]=entry
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(path.stem+'.blend')))
(OUT/'inspection.json').write_text(json.dumps(result,indent=2))
print('SOURCE_INSPECTED',[(k,len(v['objects']),[(a['name'],a['frames']) for a in v['actions']]) for k,v in result.items()])
