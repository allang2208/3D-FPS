"""Native-bound boot finish: shared vamp deformation and editable baking source.

Run with Blender in background mode. No preview rendering or gameplay tests.
"""
import json,hashlib,math
from pathlib import Path
import numpy as np
import bpy
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/BootFinishR8';O=R/'Authored';O.mkdir(exist_ok=True)
source=R/'Inputs/boots.json';d=json.loads(source.read_text(encoding='utf-8-sig'))
p=np.asarray(d['positions'],dtype=np.float64);tri=np.asarray(d['triangles'],dtype=np.int32);slots=np.asarray(d['triangle_materials'])
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def field(q):
    # Both linings and stitches receive the same smooth displacement, so no
    # layer slides or opens away from its upper. Sole/contact plane stays fixed.
    x=np.abs(q[:,0])-13.58361;y=q[:,1]+.32070;z=q[:,2]
    v=x*.1689+y*.98563;u=x*.98563-y*.1689
    env=smooth(2.2,4.3,z)*(1-smooth(11.8,15.0,z))*(1-smooth(3.0,5.8,np.abs(u)))
    env*=smooth(2.5,4.6,v)*(1-smooth(12.5,15.4,v))
    out=np.zeros(len(q))
    for center,amplitude,width,curve in [(6.1,.080,.48,.047),(8.8,.057,.56,-.025),(11.1,.034,.62,.037)]:
        t=(v-center-curve*u*u-.10*u)/width
        # Soft raised shoulder flanking the compression valley.
        out+=amplitude*(-np.exp(-t*t)+.42*np.exp(-((t-1.45)/1.15)**2))
    return out*env*(1+.045*np.sign(q[:,0]))
moving=np.zeros(len(p),dtype=bool)
moving[np.unique(tri[np.isin(slots,[0,1,3,4,6])])]=True
delta=field(p)*moving;p[:,2]+=delta
old=np.asarray(d['positions'],dtype=np.float64);eps=.012;gradient=[]
for axis in range(3):
    step=np.zeros(3);step[axis]=eps;gradient.append((field(old+step)-field(old-step))/(2*eps)*moving)
grad=np.stack(gradient,-1);norm=np.asarray(d['normals'],dtype=np.float64);g=grad[tri]
nz=norm[:,:,2]/(1+g[:,:,2]);norm[:,:,0]-=g[:,:,0]*nz;norm[:,:,1]-=g[:,:,1]*nz;norm[:,:,2]=nz
norm/=np.maximum(np.linalg.norm(norm,axis=2,keepdims=True),1e-12)
d['binding_source']=d.pop('source');d['material_slots']=[m['slot'] for m in d['materials']]
d['positions']=p.tolist();d['normals']=norm.tolist()
(O/'boots.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')

bpy.ops.wm.read_factory_settings(use_empty=True)
mesh=bpy.data.meshes.new('NunBoots_R8_NATIVE_GAME');mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in p],[],tri.tolist());mesh.update()
game=bpy.data.objects.new('GAME_NunBoots_R8',mesh);bpy.context.collection.objects.link(game)
for name in d['material_slots']:
    mat=bpy.data.materials.new(name);mesh.materials.append(mat)
for f,s in zip(mesh.polygons,slots):f.material_index=int(s);f.use_smooth=True
uv=mesh.uv_layers.new(name='NativeMetricUV')
for f,tuv in zip(mesh.polygons,d['uv']):
    for li,coord in zip(f.loop_indices,tuv):uv.data[li].uv=(coord[0],1-coord[1])
mesh.normals_split_custom_set([(n[0],-n[1],n[2]) for ns in d['normals'] for n in ns])
for bone in d['bones']:game.vertex_groups.new(name=bone['name'])
for i,weights in enumerate(d['weights']):
    for bone,weight in weights:game.vertex_groups[int(bone)].add([i],float(weight),'REPLACE')
game['native_skeleton']=d['skeleton'];game['binding_source']=d['binding_source'];game['export_contract']='Authored/boots.json; UE native coordinates, weights, per-corner normals and UVs'

# Editable detail source, explicitly excluded from the runtime export.
# Source displacement is baked from the same physical centimetre height field.
high=game.copy();high.data=game.data.copy();high.name='HIGH_BAKE_ONLY_NunBoots_R8';bpy.context.collection.objects.link(high)
high.vertex_groups.clear();bpy.context.view_layer.objects.active=high;high.select_set(True)
sub=high.modifiers.new('Baking subdivision only','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=1;sub.render_levels=1
high.hide_render=True;high.hide_set(True);high['runtime_export']=False
high['surface_height_source']='Textures/NunBootLeather_height_cm.npy; 25 cm metric tile; microdetail is in the normal atlas'
bpy.ops.wm.save_as_mainfile(filepath=str(R/'NunBoots_R8.blend'))
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'game_vertices':len(p),'game_triangles':len(tri),'max_vamp_displacement_cm':float(np.max(np.abs(delta))),'native_weights_unchanged':True,'native_uv_unchanged':True,'sole_contact_plane_unchanged':True,'runtime_tested':False,'preview_rendered':False}
(R/'authored.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NUN_BOOT_R8_AUTHORED',json.dumps(report),flush=True)
