"""Prepare editable copies and mechanical group metadata for assembly authoring."""
import bpy,json,collections
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/GunAssemblyCatalog20260928'
catalog=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
out=[]
for source in catalog['weapons']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=source['fbx'],use_anim=False)
    row={'key':source['key'],'objects':[]}
    for obj in bpy.context.scene.objects:
        if obj.type=='ARMATURE':
            row['rig']=obj.name
            row['weapon_bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None} for b in obj.data.bones if any(s in b.name.lower() for s in ['wpn','weapon','slide','bolt','mag','cyl','stock','grip','belt'])]
        if obj.type!='MESH':continue
        labels={g.index:g.name for g in obj.vertex_groups}
        dominant={v.index:labels[max(v.groups,key=lambda x:x.weight).group] if v.groups else '' for v in obj.data.vertices}
        groups=collections.Counter()
        for face in obj.data.polygons:
            bone=collections.Counter(dominant[v] for v in face.vertices).most_common(1)[0][0]
            groups[bone]+=1
        row['objects'].append({'name':obj.name,'faces':len(obj.data.polygons),'materials':[m.name if m else None for m in obj.data.materials],
            'bone_faces':dict(groups)})
    dest=ROOT/'Sources'/(source['key']+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(dest))
    out.append(row)
    (ROOT/'source-groups.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('ASSEMBLY_EDITABLE_SOURCES_PREPARED '+str(len(out)))
