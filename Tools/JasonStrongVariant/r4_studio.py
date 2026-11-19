"""Use Jason's native texture exports and identical cameras on the R3/R4 comparison."""
import bpy,sys,ast,math,json
from pathlib import Path
import numpy as np
from mathutils import Vector
here=Path(__file__).resolve().parent;sys.path.insert(0,str(here))
from r4_pose import BASE,OUT,pose_values
r3=BASE/'R3_ArmsRefined'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Jason_StrongTall_R4.blend'))
head=json.loads((r3/'head_source.json').read_text());before=json.loads((r3/'AnatomyReview/derived_saved_mesh.json').read_text())
forms=json.loads((OUT/'Review/forms.json').read_text());after=dict(before,positions=forms['base'])
datasets=[before,after];before['head_z_cm']=after['head_z_cm']=4.5
def review_apply_forms(data,bind,posed):
    p=np.asarray(data['positions']).copy()
    if data is before:return p,{}
    values=pose_values(data,bind,posed)
    for name,w in values.items():
        a=np.array(forms['targets'][name]);p[a[:,0].astype(int)]+=w*a[:,1:]
    return p,values
tree=ast.parse((here/'render_anatomy_review.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('pose','elbow_axis','rotation')],type_ignores=[]),'<pose>','exec'))
s=bpy.context.scene;cam=s.camera
bodies=[bpy.data.objects[n] for n in ['Jason_StrongTall_R3_Comparison','Jason_StrongTall_R4']]
heads=[bpy.data.objects[n] for n in ['Jason_OriginalHead','Jason_UnchangedHead']]
for ob in heads:ob.data=ob.data.copy()
for ob in bodies+heads:
    ob.modifiers.clear()
    if ob.data.shape_keys:ob.shape_key_clear()
    ob.location.z=0
s.render.resolution_x=1450;s.render.resolution_y=650;s.render.resolution_percentage=100
s.cycles.samples=22
for mode,name,angle,spacing,scale,cz in [('elbows','05_elbow_skin',-60,.42,1.75,1.33),('rest','06_chest_skin',-26,.445,1.94,1.45)]:
    for i,data in enumerate(datasets):
        q,h,_,_=pose(data,mode)
        for ob,arr in [(bodies[i],q),(heads[i],h)]:
            ob.location.x=spacing if i==0 else -spacing;ob.rotation_euler.z=math.radians(angle)
            ob.data.vertices.foreach_set('co',(arr*.01).ravel());ob.data.update()
    cam.location=(0,6,cz+.09);cam.rotation_euler=(Vector((0,0,cz))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=scale;s.render.filepath=str(OUT/'Review'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
