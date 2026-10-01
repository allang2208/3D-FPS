"""Scoped Blender revision: one-surface nameplates and volumetric guardrails.

No render, gameplay run or automatic acceptance. Original V1 sources stay available.
"""
import json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
EQUIPMENT=HALL/'Equipment20260930'
sys.path.insert(0,str(EQUIPMENT/'Scripts'))
import author_equipment as equipment
import mesh_helpers as g
CFG=json.loads((HALL/'Config/room.json').read_text(encoding='utf-8'))
BASE='/Game/Dungeons/IncineratorHall20260929/SceneFixV2'

def solid_nameplate(c,width,height,surface,axis=(0,-1,0),thickness=.004,backing='steel'):
    """Use the actual front of the solid backing, not a second coplanar decal mesh."""
    n,u,v=g.basis(axis);c=Vector(c);start=len(g.F)
    dims=(width,thickness,height) if abs(n.y)>.9 else (thickness,width,height) if abs(n.x)>.9 else (width,height,thickness)
    g.box(c-n*thickness*.5,dims,backing,.0006)
    for i in range(start,len(g.F)):
        verts=[Vector(g.V[j]) for j in g.F[i]]
        # The support skin is bevelled, with one flat front polygon.
        if all(abs((p-c).dot(n))<.000002 for p in verts):
            g.UV[i]=[g.tex(surface,.5+(p-c).dot(u)/width,.5-(p-c).dot(v)/height) for p in verts]

def corrected_nameplate(c,width,height,surface,axis=(0,-1,0),thickness=.004,backing='steel'):
    # The hydraulic service plate belongs on the masonry cheek. Seat a real
    # 4 mm plate 4 mm from the wall, instead of floating 126 mm in front of it.
    if surface=='service' and c[0]<-1.5:
        c=(c[0],.008,c[2])
        for x in (c[0]-width*.42,c[0]+width*.42):
            g.lathe((x,0,c[2]),axis,[(0,.0045),(.004,.0045)],'steel',16)
        solid_nameplate(c,width,height,surface,axis,thickness,backing)
        for x in (c[0]-width*.42,c[0]+width*.42):g.bolt((x,c[1]+.0002,c[2]),axis,.35)
        return
    solid_nameplate(c,width,height,surface,axis,thickness,backing)

def rails_layout():
    specs=[]
    def add(a,b,height=1.10):
        # A 2 cm leftover beside the stair mouth is covered by the neighbouring
        # end post; do not stack two additional posts into that seam.
        if (Vector(b)-Vector(a)).length>.20:specs.append({'a':list(a),'b':list(b),'height':height})
    pit=CFG['ash_pit'];x0,y0,x1,y1=pit['rect'];mid=pit.get('recovery_centre_x',(x0+x1)/2)
    rw=pit['recovery_width'];run=pit['recovery_steps']*pit['recovery_going']
    for lo,hi in ((x0,mid-rw/2),(mid+rw/2,x1)):add((lo,y1+.08,0),(hi,y1+.08,0))
    for x in (x0-.08,x1+.08):add((x,y0,0),(x,y1,0))
    add((x0,y0-.08,0),(x1,y0-.08,0))
    for x in (mid-rw/2-.08,mid+rw/2+.08):add((x,y1-run,pit['floor']+.15),(x,y1,0),.98)
    o=CFG['observation'];x0,x1=o['x'];y0,y1=o['y'];top=o['top'];sy=o['stairs_centre_y'];sw=o['stairs_width']
    add((x0,y0+.06,top),(x1,y0+.06,top));add((x0,y1-.05,top),(x1,y1-.05,top))
    for sign in (-1,1):
        landing=sign*7.;foot=sign*(7.+o['steps']*o['going'])
        for y in (sy-sw/2+.08,sy+sw/2-.08):add((foot,y,.15),(landing,y,top))
        add((landing,sy+sw/2+.03,top),(landing,y1-.05,top))
        add((landing,y0+.06,top),(landing,sy-sw/2-.02,top))
    return specs

def rail_prism(a,b,zlo,zhi,width):
    a,b=Vector(a),Vector(b);along=(b-a);along.z=0;along.normalize();side=Vector((-along.y,along.x,0))
    vs=[tuple(p+side*s*width*.5+Vector((0,0,z))) for p in (a,b) for s,z in ((-1,zlo),(1,zlo),(1,zhi),(-1,zhi))]
    fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return vs,fs

def rail_bar(a,b,zlo,zhi,width,surface):
    vs,fs=rail_prism(a,b,zlo,zhi,width)
    for ids in fs:
        verts=[Vector(vs[i]) for i in ids]
        normal=(verts[1]-verts[0]).cross(verts[2]-verts[0]);axis=max(range(3),key=lambda k:abs(normal[k]));dims=[k for k in range(3) if k!=axis]
        lo=[min(p[k] for p in verts) for k in dims];hi=[max(p[k] for p in verts) for k in dims]
        uv=[(.015+.97*(p[dims[0]]-lo[0])/max(hi[0]-lo[0],.00001),.985-.97*(p[dims[1]]-lo[1])/max(hi[1]-lo[1],.00001)) for p in verts]
        g.face(verts,surface,uv)

def author_rails():
    for index,spec in enumerate(rails_layout()):
        a,b=Vector(spec['a']),Vector(spec['b']);height=spec['height'];length=(b-a).length
        equipment.part('Rail_Run_%02d'%index)
        # Eight-centimetre wide top rail provides a flat, continuous handhold.
        rail_bar(a,b,height-.04,height+.04,.08,'teal')
        rail_bar(a,b,.48,.56,.06,'teal')
        rail_bar(a,b,.035,.155,.015,'graphite')
        count=max(1,math.ceil(length/1.25));yaw=math.atan2(b.y-a.y,b.x-a.x)
        for i in range(count+1):
            p=a+(b-a)*i/count
            g.box(p+Vector((0,0,height*.5)),(.080,.080,height),'teal',.003,(0,0,yaw))
            g.box(p+Vector((0,0,.010)),(.150,.150,.020),'steel',.002,(0,0,yaw))
            for dx in (-.053,.053):
                for dy in (-.053,.053):g.bolt(p+Vector((dx*math.cos(yaw)-dy*math.sin(yaw),dx*math.sin(yaw)+dy*math.cos(yaw),.021)),(0,0,1),.60)

def cube(center,size):
    c=Vector(center);x,y,z=(s*.5 for s in size)
    vs=[tuple(c+Vector(v)) for v in [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]]
    return vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]

def export(key,author,colliders,mat,suffix='_V2'):
    g.V.clear();g.F.clear();g.UV.clear();g.SMOOTH.clear();equipment.PARTS.clear();equipment.CURRENT=None
    author();equipment.CURRENT['last_vertex']=len(g.V)
    name='SM_Incinerator_'+key+suffix;mesh=bpy.data.meshes.new(name);mesh.from_pydata(g.V,[],g.F);mesh.materials.append(mat);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    uv=mesh.uv_layers.new(name='UVMap')
    for p,coords,smooth in zip(mesh.polygons,g.UV,g.SMOOTH):
        p.use_smooth=smooth
        for li,coord in zip(p.loop_indices,coords):uv.data[li].uv=coord
    for part in equipment.PARTS:
        vg=obj.vertex_groups.new(name=part['name']);vg.add(list(range(part['first_vertex'],part['last_vertex'])),1,'REPLACE')
    src=obj.copy();src.data=obj.data.copy();src.name='EDIT_'+key;src.location.y=25;src.hide_render=True;bpy.context.collection.objects.link(src)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000003);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    normal=obj.modifiers.new('Manufactured weighted normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=40;bpy.ops.object.modifier_apply(modifier=normal.name)
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
    mesh=obj.data;uv=mesh.uv_layers.active.data
    for p in mesh.polygons:
        ids=list(p.loop_indices);a,b,c=(uv[i].uv.copy() for i in ids)
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1e-12:continue
        verts=[mesh.vertices[mesh.loops[i].vertex_index].co for i in ids];axis=max(range(3),key=lambda k:abs(p.normal[k]));dims=[k for k in range(3) if k!=axis];center=sum(verts,Vector())/3
        for li,v in zip(ids,verts):uv[li].uv=g.tex('steel',.5+(v[dims[0]]-center[dims[0]])*.2,.5-(v[dims[1]]-center[dims[1]])*.2)
    collision_objects=[]
    for i,(vs,fs) in enumerate(colliders):
        cm=bpy.data.meshes.new(f'UCX_{name}_{i:02d}');cm.from_pydata(vs,[],fs);cm.update()
        bm=bmesh.new();bm.from_mesh(cm);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cm);bm.free()
        co=bpy.data.objects.new(cm.name,cm);bpy.context.collection.objects.link(co);collision_objects.append(co)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    for co in collision_objects:co.select_set(True)
    bpy.context.view_layer.objects.active=obj;fbx=ROOT/'Authored'/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    for co in collision_objects:co.hide_viewport=True;co.hide_render=True
    print('INCINERATOR_FIX_AUTHORED',key,len(mesh.polygons),len(colliders),flush=True)
    return {'key':key,'name':name,'fbx':str(fbx),'material':g.MATERIAL,'triangles':len(mesh.polygons),'collision_boxes_or_convexes':len(colliders),'collision_policy':'simple_and_complex','ue_path':BASE+'/Meshes/'+name}

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';mat=equipment.material()
    equipment.plaque=corrected_nameplate
    door_colliders=[cube((0,-.035,1.65),(2.44,.32,2.90)),cube((-1.57,.19,1.85),(.53,.55,2.12)),cube((0,.25,1.86),(.62,.45,.63))]
    records=[export('FurnaceDoorKit',equipment.door,door_colliders,mat)]
    specs=rails_layout();rail_colliders=[rail_prism(s['a'],s['b'],-.025,s['height']+.04,.08) for s in specs]
    records.append(export('Railings',author_rails,rail_colliders,mat))
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/Incinerator_Nameplate_Railings_V2.blend'))
    (ROOT/'Authored/manifest.json').write_text(json.dumps({'revision':'incinerator_label_railings_v2_20260930','objects':records,'tests_run':False,'rendered':False},indent=2),encoding='utf-8')
    (ROOT/'Config/railings.json').write_text(json.dumps({'runs':specs,'top_width_m':.08,'upright_size_m':.08,'simple_collision':'one closed convex prism per run, including sloped rails','visual_collision':'complex triangles for complex traces','ash_pit':'retained existing 1.2 m maintenance pit; no lower floor added'},indent=2),encoding='utf-8')

if __name__=='__main__':build()
