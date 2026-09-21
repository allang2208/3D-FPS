"""Repair V05 geometry and cloth authoring, retaining the original Meshy surface.

No new character generation, motion baking, preview render or game test.
"""
import bpy, json, math, sys, shutil
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import layered_v04 as common
import original_robe_v05 as prior
OUT=ROOT/'Authoring/CleanRobeV06'
DEL=ROOT/'Delivery/CleanRobeV06'
OLD=ROOT/'Authoring/OriginalRobeV05'
ROLES=['Idle','Walk','CastPoison','ThrowPoisonBottle','DeathBackward']
KEEP=['Witch_Hat','Witch_Head_Hair','Witch_Hand_Left','Witch_Hand_Right',
      'Witch_UpperRobe','Witch_OriginalRobe_Render','Witch_OriginalFeet']

def weights(ob,i):
    return {ob.vertex_groups[g.group].name:g.weight for g in ob.data.vertices[i].groups if g.weight>1e-7}

def mix(a,b,t):
    return {n:a.get(n,0)*(1-t)+b.get(n,0)*t for n in a.keys()|b.keys()}

def index_map(ob):return {int(s):i for i,s in enumerate(ob['source_vertex_indices'])}

def nearest_tree(ob,indices=None):
    ids=list(range(len(ob.data.vertices))) if indices is None else list(indices)
    tree=KDTree(len(ids))
    for i in ids:tree.insert(ob.data.vertices[i].co,i)
    tree.balance();return tree

def repair_seams(robe,upper,feet):
    rim=index_map(robe);uim=index_map(upper);fim=index_map(feet)
    ankle_ids=rim.keys()&fim.keys();waist_ids=rim.keys()&uim.keys()
    foot_tree=nearest_tree(feet)
    for v in robe.data.vertices:
        p,i,d=foot_tree.find(v.co)
        # The ankle region shares the original foot skin. Cloth is fixed here;
        # blend into the hip-supported garment over a broad 15 cm transition.
        t=common.smooth((.38-v.co.z)/.15)
        prior.set_weights(robe,v.index,mix({'Hips':1.},weights(feet,i),t))
    for s in ankle_ids:prior.set_weights(robe,rim[s],weights(feet,fim[s]))
    waist_tree=nearest_tree(upper,[uim[s] for s in waist_ids])
    for v in upper.data.vertices:
        p,i,d=waist_tree.find(v.co)
        if d<.05:prior.set_weights(upper,v.index,mix(weights(upper,v.index),{'Hips':1.},1-common.smooth(d/.05)))
    for s in waist_ids:
        prior.set_weights(upper,uim[s],{'Hips':1.});prior.set_weights(robe,rim[s],{'Hips':1.})
    return {'ankle_shared_vertices':len(ankle_ids),'waist_shared_vertices':len(waist_ids),
            'ankle_skin_transition_m':[.23,.38],'cloth_fixed_below_m':.26,'cloth_fixed_above_m':.82}

def cloth_proxy(robe,rig):
    robe.data.calc_loop_triangles()
    bvh=BVHTree.FromPolygons([v.co for v in robe.data.vertices],
        [tuple(t.vertices) for t in robe.data.loop_triangles],all_triangles=True)
    N=64;ROWS=36;zs=np.linspace(.98,.022,ROWS+1);radii=np.zeros((ROWS+1,N))
    # Every point remains on its radial half-line. Ray misses interpolate radii,
    # never project across a hole to an unrelated face and overwrite its Z.
    for j,z in enumerate(zs):
        c=Vector((0,.045,float(z)));valid={}
        for i in range(N):
            a=i/N*math.tau;d=Vector((math.sin(a),-math.cos(a),0))
            p,no,idx,dist=bvh.ray_cast(c+d*.60,-d,.56)
            if p is not None:
                radius=(p-c).dot(d)
                if .07<radius<.43:valid[i]=radius
        if len(valid)>=4:
            keys=sorted(valid);xp=[i-N for i in keys]+keys+[i+N for i in keys]
            fp=[valid[i] for i in keys]*3;radii[j]=np.interp(np.arange(N),xp,fp)
        else:
            band=[v.co for v in robe.data.vertices if abs(v.co.z-z)<.055]
            rx=max(.13,min(.34,float(np.quantile([abs(p.x) for p in band],.90)))) if band else .22
            ry=max(.12,min(.30,float(np.quantile([abs(p.y-.045) for p in band],.90)))) if band else .19
            for i in range(N):
                a=i/N*math.tau;radii[j,i]=1/math.sqrt((math.sin(a)/rx)**2+(math.cos(a)/ry)**2)
    for _ in range(8):radii=.5*radii+.25*np.roll(radii,1,axis=1)+.25*np.roll(radii,-1,axis=1)
    for _ in range(4):radii[1:-1]=.5*radii[1:-1]+.25*radii[:-2]+.25*radii[2:]
    radii=np.clip(radii,.085,.39)
    pts=[(float(radii[j,i])*math.sin(i/N*math.tau),.045-float(radii[j,i])*math.cos(i/N*math.tau),float(z))
         for j,z in enumerate(zs) for i in range(N)]
    faces=[(j*N+i,(j+1)*N+i,(j+1)*N+(i+1)%N,j*N+(i+1)%N) for j in range(ROWS) for i in range(N)]
    me=bpy.data.meshes.new('Witch_Robe_SimProxyV06');me.from_pydata(pts,[],faces)
    ob=bpy.data.objects.new('Witch_Robe_SimProxyV06',me);bpy.context.collection.objects.link(ob)
    mat=bpy.data.materials.new('M_Witch_SimProxyV06');mat.use_nodes=True
    bs=mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled');bs.inputs['Base Color'].default_value=(0,.3,.6,1)
    output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
    me.materials.append(mat)
    robe_tree=nearest_tree(robe)
    for v in me.vertices:
        p,i,d=robe_tree.find(v.co)
        prior.set_weights(ob,v.index,weights(robe,i) if v.co.z<.40 else {'Hips':1.})
    mod=ob.modifiers.new('Skin','ARMATURE');mod.object=rig
    ob.hide_render=True;ob.display_type='WIRE'
    ob['role']='Cloth extraction only. Hip/ankle anchors; continuous radial cage. Never export as render geometry.'
    return ob

def main():
    for d in [OUT,OUT/'Parts',OUT/'MotionLayers',DEL]:d.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(OLD/'Witch_OriginalRobeV05.blend'))
    rig=common.rig();common.neutral(rig)
    for ob in list(bpy.context.scene.objects):
        if ob.type=='MESH' and ob.name not in KEEP:bpy.data.objects.remove(ob,do_unlink=True)
    robe=bpy.data.objects['Witch_OriginalRobe_Render'];upper=bpy.data.objects['Witch_UpperRobe'];feet=bpy.data.objects['Witch_OriginalFeet']
    seam=repair_seams(robe,upper,feet)
    robe.data.materials[0]=robe.data.materials[0].copy();robe.data.materials[0].name='M_Witch_OriginalRobeV06'
    proxy=cloth_proxy(robe,rig)
    meshes=[bpy.data.objects[n] for n in KEEP]
    for ob in meshes:
        ob.hide_render=False;ob.hide_set(False)
        common.save_part(OUT/'Parts'/(ob.name+'.blend'),[rig,ob])
        common.export(OUT/'Parts'/(ob.name+'.fbx'),[rig,ob])
    common.save_part(OUT/'Parts'/'Witch_Robe_SimProxyV06.blend',[rig,proxy])
    common.export(OUT/'Parts'/'Witch_Robe_SimProxyV06.fbx',[rig,proxy])
    bpy.context.scene['revision']='CleanRobeV06: original surfaces, no donor body, shared seam skin, limited cloth.'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Witch_CleanRobeV06.blend'))
    proxy.hide_render=False
    common.export(DEL/'SK_Witch_CleanRobeV06_ClothBuildSource.fbx',[rig]+meshes+[proxy])
    proxy.hide_render=True
    common.export(DEL/'SK_Witch_CleanRobeV06.fbx',[rig]+meshes)
    manifest={'revision':'CleanRobeV06','render_objects':KEEP,'excluded_donor_objects':['Witch_InnerBody.001','Witch_InnerCalves'],
        'proxy_vertices':len(proxy.data.vertices),'proxy_faces':len(proxy.data.polygons),'seams':seam,
        'original_visible_positions_uv_normals_preserved':True,'animation_keys_changed':False,
        'cloth_max_distance_cm':6,'cloth_render_part':'Witch_OriginalRobe_Render','runtime_tested':False}
    (OUT/'body_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    # Replace geometry in editable motion sources, retaining their existing keys.
    sources=[(OLD/f'Witch_{role}_OriginalRobeV05.blend',OUT/f'Witch_{role}_CleanRobeV06.blend') for role in ROLES]
    sources.extend((p,OUT/'MotionLayers'/p.name) for p in (OLD/'MotionLayers').glob('*.blend'))
    for source,destination in sources:
        bpy.ops.wm.open_mainfile(filepath=str(source))
        rig=common.rig()
        for ob in list(bpy.context.scene.objects):
            if ob.type=='MESH':bpy.data.objects.remove(ob,do_unlink=True)
        with bpy.data.libraries.load(str(OUT/'Witch_CleanRobeV06.blend'),link=False) as (src,dst):
            dst.objects=[n for n in src.objects if n in KEEP or n=='Witch_Robe_SimProxyV06']
        for ob in dst.objects:
            bpy.context.collection.objects.link(ob)
            for mod in ob.modifiers:
                if mod.type=='ARMATURE':mod.object=rig
        bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    for role in ROLES:
        shutil.copy2(ROOT/f'Delivery/OriginalRobeV05/A_Witch_{role}_OriginalRobeV05.fbx',DEL/f'A_Witch_{role}_CleanRobeV06.fbx')
    shutil.copy2(OLD/'motion_manifest.json',OUT/'motion_manifest.json')
    print('CLEAN_ROBE_V06_AUTHORED '+json.dumps(manifest),flush=True)

if __name__=='__main__':main()
