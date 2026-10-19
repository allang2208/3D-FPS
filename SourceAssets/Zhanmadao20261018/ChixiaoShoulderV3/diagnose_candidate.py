from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/SourceAssets/Zhanmadao20261018/ChixiaoShoulderV3/author_root.py')
e={'__file__':str(p)}
exec(compile(p.read_text('utf-8').split('for variant in')[0],'helpers','exec'),e)
exec('''
bpy.ops.wm.open_mainfile(filepath=str(V2/'LongGrip/Chixiao_GripV2_Editable.blend'))
clip=json.loads((V2/'LongGrip/editable_keys.json').read_text())
w=A.pose_from_rows(clip['samples'][65]['bones']);idle=A.pose_from_rows(clip['samples'][-1]['bones'])
ref={n:A.canonical(A.native(row)) for n,row in A.DATA['reference'].items()}
bindings=[]
for ob in bpy.context.scene.objects:
 if ob.type=='MESH' and ob.vertex_groups:bindings+=boundary_skin(ob,ref)
points=skin_points(w,bindings);hand=np.array(w['hand_r'].translation);elbow=np.array(w['lowerarm_r'].translation)
r=np.cross(points.mean(axis=0)-elbow,-normal);r/=np.linalg.norm(r)
l=np.cross(points.mean(axis=0)-hand,-normal);l/=np.linalg.norm(l)
hq=w['hand_r'].to_quaternion()@idle['hand_r'].to_quaternion().inverted();wa=hq@(idle['hand_r'].translation-idle['lowerarm_r'].translation).normalized()
print('DIAGNOSTIC',len(bindings),'pivot',hand.tolist(),elbow.tolist(),'centroid',points.mean(axis=0).tolist(),'axes',r.tolist(),l.tolist(),flush=True)
for deg in range(-30,61,5):
 m=rotated(points,hand,l,math.radians(deg));me=rotated(elbow[None,:],hand,l,math.radians(deg))[0]
 best=min((float((rotated(m,me,r,math.radians(t))@normal).max()*100),t) for t in range(-80,121))
 print('CANDIDATE',deg,'wrist',math.degrees(wa.angle(Vector(hand-me))),'min_plane',best,flush=True)
''',e)