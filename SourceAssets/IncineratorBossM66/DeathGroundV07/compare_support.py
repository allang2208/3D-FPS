"""Compare the saved collision shapes with the current mesh in the source death poses."""
import bpy,json,re,itertools,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'DeathGroundV07'
data=json.loads((ROOT/'Records/death_inputs.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(BASE/'SurfaceLifeV05/Authoring/M66_surface_life_v05.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body']
with bpy.data.libraries.load(str(BASE/'ReactionsV03/Authoring/M66_reactions_v03.blend')) as (source,target):
    target.actions=['A_M66_Death_V03']
rig.animation_data_create();rig.animation_data.action=target.actions[0]
if target.actions[0].slots:rig.animation_data.action_slot=target.actions[0].slots[0]
report=[]
for pose in data['poses']:
    bpy.context.scene.frame_set(round(pose['time']*60));bpy.context.view_layer.update()
    evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    p=np.empty(len(evaluated.data.vertices)*3);evaluated.data.vertices.foreach_get('co',p)
    visual_min=float(p.reshape(-1,3)[:,2].min())*100
    shapes=[]
    for body in data['bodies']:
        if body['bone']=='M66_Rig':continue
        transform=pose['bones'][body['bone']]['world'];x,y,z,w=transform['rotation'];q=Quaternion((w,x,y,z))
        for shape in body['shapes']:
            if 'ShapeType=Box' not in shape:continue
            center=[float(v) for v in re.search(r'Center=\(X=([^,]+),Y=([^,]+),Z=([^\)]+)',shape).groups()]
            size=[float(re.search('Extent'+axis+r'=([^,\)]+)',shape).group(1)) for axis in 'XYZ']
            corners=[]
            for signs in itertools.product((-1,1),repeat=3):
                v=Vector([(center[i]+signs[i]*size[i]*.5)*transform['scale'][i] for i in range(3)])
                corners.append((q@v+Vector(transform['position'])).z)
            shapes.append({'bone':body['bone'],'bottom_cm':min(corners)})
    shapes.sort(key=lambda v:v['bottom_cm'])
    report.append({'time':pose['time'],'visible_surface_bottom_cm':visual_min,
        'collision_bottom_cm':shapes[0]['bottom_cm'],'collision_below_visible_cm':visual_min-shapes[0]['bottom_cm'],
        'lowest_collision_bodies':shapes[:5]})
(ROOT/'Records/support_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_DEATH_SUPPORT_INPUTS '+json.dumps(report),flush=True)
