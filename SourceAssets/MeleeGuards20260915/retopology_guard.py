"""Build clean, beveled game surfaces from a generated quillon contour."""
import bpy,bmesh,math
from mathutils import Vector

def build_guard(profile,stock_rings,id,low):
    parts=[]
    def make(name,verts,faces,width):
        data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
        for f in data.polygons:f.use_smooth=True
        obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        bevel=obj.modifiers.new('Machined bronze edge radii','BEVEL');bevel.width=width;bevel.segments=3 if low else 6
        bevel.limit_method='ANGLE';bevel.angle_limit=.45;bevel.harden_normals=True
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        normals=obj.modifiers.new('Weighted metal surface normals','WEIGHTED_NORMAL');normals.keep_sharp=True;normals.weight=50
        bpy.ops.object.modifier_apply(modifier=normals.name)
        triangles=obj.modifiers.new('Export triangles and tangent basis','TRIANGULATE')
        if hasattr(triangles,'keep_custom_normals'):triangles.keep_custom_normals=True
        bpy.ops.object.modifier_apply(modifier=triangles.name)
        parts.append(obj)
        return obj
    def smooth(t):
        t=min(1,max(0,t));return t*t*(3-2*t)
    for sign in [-1,1]:
        points,center=stock_rings[sign]
        ymin=min(p.y for p in points)-.0004;ymax=max(p.y for p in points)+.0004
        zmin=min(p.z for p in points)-.0004;zmax=max(p.z for p in points)+.0004
        yc=(ymin+ymax)/2;zc=(zmin+zmax)/2
        source_zc=sum(profile['root_z'])/2;source_zspan=profile['root_z'][1]-profile['root_z'][0]
        ratio=(zmax-zmin)/source_zspan
        length={'bastion_guard':.083,'riposte_guard':.080,'light_guard':.073}[id]
        half_tip={'bastion_guard':.013,'riposte_guard':.010,'light_guard':.007}[id]
        transformed=[]
        for x,z in profile['vertices_xz']:
            t=(x-profile['cut'])/(profile['max_x']-profile['cut'])
            scale=ratio+(1-ratio)*smooth(t/.45)
            zz=(z-source_zc)*scale+zc+smooth(t)*(source_zc-zc)
            half=half_tip
            transformed.append((sign*(.064+t*length),zz,half))
        n=len(transformed)
        verts=[(x,yc-half,z) for x,z,half in transformed]+[(x,yc+half,z) for x,z,half in transformed]
        faces=[list(t) for t in profile['triangles']]+[[i+n for i in reversed(t)] for t in profile['triangles']]
        start=0
        for end in profile['loop_ends']:
            for i in range(start,end):
                j=start if i+1==end else i+1
                faces.append([i,j,j+n,i+n])
            start=end
        make('Generated_contour_quillon_'+str(sign),verts,faces,.00085 if id=='light_guard' else .00115)
        # The 3 mm overlap sits inside the retained stock saddle. Its envelope
        # comes from every actual cut-boundary point, not one arbitrary UV loop.
        xs=[sign*.057,sign*.066]
        verts=[(x,y,z) for x in xs for y,z in [(ymin,zmin),(ymax,zmin),(ymax,zmax),(ymin,zmax)]]
        faces=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
        make('Fitted_root_sleeve_'+str(sign),verts,faces,.00045)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
    result=bpy.context.object;result.name=('Frost_Guard_' if low else 'Guard_High_')+id
    result.data.update()
    print('GUARD_ROOT_ENVELOPES',id,{str(s):{'min':[min(p[a] for p in stock_rings[s][0]) for a in range(3)],'max':[max(p[a] for p in stock_rings[s][0]) for a in range(3)]} for s in [-1,1]},flush=True)
    return result
