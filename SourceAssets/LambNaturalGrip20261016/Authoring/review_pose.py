"""Offline copy of PotionArmPose kinematics using current Traversal V7 skin.
No UE, game, savegame or production asset writes. Coordinates are UE camera cm.
"""
import json, math, sys, argparse
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=Path(__file__).resolve().parent
source=json.loads((ROOT/'SourceAssets/BenelliM4Super9020261006/EquipmentSources/rig_Traversal.json').read_text())
skin=json.loads((ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/Traversal.json').read_text())
geometry=json.loads((ROOT/'SourceAssets/LargeLamb20261014/large-lamb-geometry.json').read_text())
data=json.loads((ROOT/'Content/ColdSteelData/potion_use_motion.json').read_text())
bones=source['bones']; names={b['index']:n for n,b in bones.items()}
parent={n:names.get(b['parent']) for n,b in bones.items()}
order=sorted(bones,key=lambda n:bones[n]['index'])
def frame(x,z):
    x=x.normalized(); z=(z-x*z.dot(x)).normalized()
    return Matrix((x,z.cross(x),z)).transposed()
def xy(x,y):
    x=x.normalized(); y=(y-x*y.dot(x)).normalized()
    return Matrix((x,y,x.cross(y))).transposed()
def rot(v):
    p,y,r=map(math.radians,v)
    return Matrix.Rotation(y,3,'Z')@Matrix.Rotation(-p,3,'Y')@Matrix.Rotation(-r,3,'X')
def mat(r,p):
    m=r.to_4x4();m.translation=p;return m
rest={n:mat(Matrix([Vector(a).normalized() for a in b['axes']]).transposed(),Vector(b['position'])) for n,b in bones.items()}
inv={n:m.inverted() for n,m in rest.items()}
local={n:inv[parent[n]]@m if parent[n] else m for n,m in rest.items()}
pos=np.column_stack((skin['positions'],np.ones(len(skin['positions']))))
weights={n:np.array([w.get(n,0) for w in skin['weights']]) for n in order}
def ease(t):
    t=max(0,min(1,t));return t*t*t*(t*(t*6-15)+10)
def grip_at(m,t):
    ks=m['keys']
    def tangent(j):
        if j in (0,len(ks)-1):return Vector()
        p=Vector(ks[j]['grip'])
        if (p-Vector(ks[j-1]['grip'])).length<.01 or (p-Vector(ks[j+1]['grip'])).length<.01:return Vector()
        return (Vector(ks[j+1]['grip'])-Vector(ks[j-1]['grip']))/(ks[j+1]['time']-ks[j-1]['time'])
    for i in range(1,len(ks)):
        a,b=ks[i-1],ks[i]
        if t<=b['time']:
            dt=max(.001,b['time']-a['time']);u=max(0,min(1,(t-a['time'])/dt))
            p=Vector(a['grip'])*(2*u**3-3*u*u+1)+tangent(i-1)*dt*(u**3-2*u*u+u)+Vector(b['grip'])*(-2*u**3+3*u*u)+tangent(i)*dt*(u**3-u*u)
            q=rot(a['rotation']).to_quaternion().slerp(rot(b['rotation']).to_quaternion(),ease(u))
            return q.to_matrix(),p
    return rot(ks[-1]['rotation']),Vector(ks[-1]['grip'])
def below(n,a):
    while n:
        if n==a:return True
        n=parent[n]
    return False
def solve(m,t,skin_mesh=True):
    g,gp=grip_at(m,t); objrot=g@rot(m['object_rotation']); obj=mat(objrot,gp-objrot@Vector(m['grip_in_object']))
    goal={n:v.copy() for n,v in rest.items()}; info={}
    for s,sign in [('l',1),('r',-1)]:
        u,l,h,c=['%s_%s'%(b,s) for b in ('upperarm','lowerarm','hand','clavicle')]
        palmref=frame(rest['middle_01_'+s].translation-rest[h].translation,(rest['index_01_'+s].translation-rest[h].translation).cross(rest['pinky_01_'+s].translation-rest[h].translation)*sign)
        upright=Matrix(((1,0,0),(0,0,sign),(0,-sign,0)))
        desired=g@upright@rot(m.get('right_palm_rotation' if s=='r' else 'palm_rotation',[0,0,0]))
        targetgrip=obj@Vector(m['right_grip_in_object'] if s=='r' else m['grip_in_object'])
        target=targetgrip-desired@Vector(m['right_grip_in_palm'] if s=='r' else m['grip_in_palm'])
        shoulder=Vector(m.get('right_shoulder' if s=='r' else 'shoulder',data['shoulder']));pole=Vector(m.get('right_elbow_pole' if s=='r' else 'elbow_pole',data['elbow_pole']))
        if s=='r' and 'right_shoulder' not in m:shoulder.y*=-1
        if s=='r' and 'right_elbow_pole' not in m:pole.y*=-1
        ru=rest[l].translation-rest[u].translation;rl=rest[h].translation-rest[l].translation
        reach=target-shoulder;limit=(ru.length+rl.length)*.93
        if reach.length>limit:shoulder+=reach.normalized()*(reach.length-limit)
        d=(target-shoulder).length;direction=(target-shoulder).normalized()
        along=(ru.length_squared-rl.length_squared+d*d)/(2*d)
        bend=pole-shoulder-direction*(pole-shoulder).dot(direction)
        elbow=shoulder+direction*along+bend.normalized()*math.sqrt(max(0,ru.length_squared-along*along))
        ld=(target-elbow).normalized();ud=(elbow-shoulder).normalized()
        lower=xy(ld,desired.col[1])@xy(rl,palmref.col[1]).inverted()
        upper=(lower@ru.normalized()).rotation_difference(ud).to_matrix()@lower
        open_at=m['times']['release'] if m.get('palm_rotation') and m.get('two_handed') else m['times']['release']-.025
        closed=ease((t-m['times']['grab']*.42)/(m['times']['grab']*.58))*(1-ease((t-open_at)/.08))
        for n in order:
            if not below(n,c):continue
            if n==c:goal[n]=rest[n].copy();goal[n].translation+=shoulder-rest[u].translation
            elif n==u:goal[n]=mat(upper@rest[n].to_3x3(),shoulder)
            elif n==l:goal[n]=mat(lower@rest[n].to_3x3(),elbow)
            elif n==h:goal[n]=mat(desired@palmref.inverted()@rest[n].to_3x3(),target)
            else:
                goal[n]=goal[parent[n]]@local[n]
                bits=n.split('_')
                if len(bits)==3 and bits[0] in m['digits'] and bits[1] in ('01','02','03'):
                    digit,number,_=bits;j=int(number)-1;nxt=f'{digit}_{j+2:02}_{s}'
                    v=rest[nxt].translation-rest[n].translation if nxt in rest else rest[n].to_3x3()@rest[parent[n]].to_3x3().inverted()@(rest[n].translation-rest[parent[n]].translation)
                    dp=m.get('right_digits',{}).get(digit,m.get('right_thumb',m['digits']['thumb']) if s=='r' and digit=='thumb' else m['digits'][digit]) if s=='r' else m['digits'][digit]
                    flex=(8+j*4)*(1-closed)+dp['flex'][j]*closed
                    q=desired@Matrix.Rotation(math.radians(dp['spread'][j])*sign,3,'Z')@Matrix.Rotation(-math.radians(flex),3,'Y')@frame(v,palmref.col[2]).inverted()@rest[n].to_3x3()
                    goal[n]=mat(q,goal[n].translation)
        fore=desired.inverted()@ld
        info[s]={'wrist':list(target),'elbow':list(elbow),'shoulder':list(shoulder),'palm_axis':list(desired.col[0]),'palm_normal':list(desired.col[2]),'wrist_swing_deg':math.degrees(math.acos(max(-1,min(1,fore.x)))),'wrist_flex_deg':math.degrees(math.atan2(fore.z,fore.x)),'wrist_deviation_deg':math.degrees(math.atan2(fore.y,fore.x))}
    verts=None
    if skin_mesh:
        verts=np.zeros((len(pos),3))
        for n in order:
            if np.any(weights[n]):verts+=(pos@np.array(goal[n]@inv[n]).T)[:,:3]*weights[n][:,None]
    return verts, obj, goal, info
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
def mesh(name,verts,faces,material):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update();o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(material)
    for p in d.polygons:p.use_smooth=True
    return o
def render(m,t,label):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    verts,obj,goal,info=solve(m,t)
    hands=mesh('Current V7 skinned hands',verts.tolist(),[list(reversed(f)) for f in skin['triangles']],material('Skin',(0.56,.32,.20)))
    meat=mesh('Unchanged roast lamb',[list(obj@Vector(v)) for v in geometry['vertices']],geometry['faces'],material('Roast',(.24,.095,.028)))
    for ob,colors in [(hands,[(.56,.32,.20,1)]*len(verts)),(meat,[(*rgb[:3],1) for rgb in geometry['vertex_rgb_linear']])]:
        attr=ob.data.color_attributes.new(name='SurfaceColor',type='FLOAT_COLOR',domain='POINT')
        attr.data.foreach_set('color',np.array(colors).ravel());ob.data.color_attributes.active_color=attr
    center=obj@Vector((1,0,3))
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.world.color=(.04,.04,.04);scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.6
    scene.display.shading.color_type='VERTEX';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD';scene.view_settings.view_transform='Standard'
    camdata=bpy.data.cameras.new('Offline camera');cam=bpy.data.objects.new('Offline camera',camdata);bpy.context.collection.objects.link(cam);scene.camera=cam
    for view,offset,scale in [('front',Vector((-65,0,16)),44),('side',Vector((-12,65,10)),44),('top',Vector((0,0,75)),48)]:
        cam.location=center+offset;cam.rotation_euler=(-offset).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=scale
        scene.render.filepath=str(OUT/f'{label}_{view}.png');bpy.ops.render.render(write_still=True)
    (OUT/f'{label}_pose.json').write_text(json.dumps(info,indent=2))
    if label.startswith('final_'):
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{label}.blend'))
    print(label,json.dumps(info),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--motion');ap.add_argument('--label',default='before');ap.add_argument('--time',type=float,default=2.75)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    motion=json.loads(Path(args.motion).read_text()) if args.motion else data['roasted_large_lamb']
    render(motion,args.time,args.label)
