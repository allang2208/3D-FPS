"""Rest-space garment clearance, articulated skirt support and close-range surfaces."""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
OUT=ROOT/'Refinement20260922'
REV='Refinement03'

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)

def apply(rig):
    if rig.get('surface_revision')==REV:return
    rest={b.name:(rig.matrix_world@b.matrix_local).translation for b in rig.data.bones}
    waist=rest['pelvis'].z
    knee=(rest['calf_l'].z+rest['calf_r'].z)*.5
    center=Vector((0,-.015,0))
    capsules=[]
    for side in ('l','r'):
        capsules.extend([(rest['thigh_'+side],rest['calf_'+side],.105),
                         (rest['calf_'+side],rest['foot_'+side],.072)])
    def clearance(p):
        radial=Vector((p.x-center.x,p.y-center.y,0));distance=radial.length
        if distance<.001:return p.copy()
        direction=radial/distance;required=0.
        for a,b,radius in capsules:
            t=max(0.,min(1.,(p.z-a.z)/(b.z-a.z)))
            c=a.lerp(b,t);vertical=abs(p.z-c.z)
            if vertical>radius:continue
            radius=math.sqrt(max(0,radius*radius-vertical*vertical))+.012
            v=Vector((c.x-center.x,c.y-center.y,0));project=v.dot(direction)
            cross=v.length_squared-project*project
            if cross<radius*radius:required=max(required,project+math.sqrt(radius*radius-cross))
        return p+direction*max(0.,required-distance)
    def skirt_weights(p):
        support=.98*smooth((waist-p.z-.055)/.22)
        calf=smooth((knee+.075-p.z)/.16)
        left=smooth((p.x+.045)/.09)
        return {'pelvis':1-support,'thigh_l':support*(1-calf)*left,
                'thigh_r':support*(1-calf)*(1-left),'calf_l':support*calf*left,
                'calf_r':support*calf*(1-left)}
    def weights(obj):
        obj.vertex_groups.clear()
        for name in ('pelvis','thigh_l','thigh_r','calf_l','calf_r'):obj.vertex_groups.new(name=name)
        for v in obj.data.vertices:
            for name,w in skirt_weights(v.co).items():
                if w>1e-6:obj.vertex_groups[name].add([v.index],w,'REPLACE')
    skirt=bpy.data.objects['Witch_OriginalRobe_Render']
    moved=[]
    for v in skirt.data.vertices:
        old=v.co.copy();v.co=clearance(old);moved.append((v.co-old).length)
    weights(skirt)
    # Use the inner radial percentile, so most render vertices sit outside their
    # simulation support instead of far inside an oversized bell-shaped proxy.
    proxy=bpy.data.objects['WitchRebuilt_SimulationProxy'];raw=[v.co.copy() for v in skirt.data.vertices]
    n=64;rows=33;radii=[]
    for j in range(rows):
        z=waist*(1-j/(rows-1))+.078*j/(rows-1)
        for i in range(n):
            a=2*math.pi*i/n;direction=Vector((math.cos(a),math.sin(a),0))
            nearby=sorted((p-center).xy.length for p in raw if abs(p.z-z)<.035 and
                Vector((p.x-center.x,p.y-center.y,0)).normalized().dot(direction)>math.cos(.12))
            radii.append(nearby[int((len(nearby)-1)*.35)] if nearby else .21+.08*j/(rows-1))
    for _ in range(3):
        old=radii[:]
        for j in range(rows):
            for i in range(n):radii[j*n+i]=.6*old[j*n+i]+.2*(old[j*n+(i-1)%n]+old[j*n+(i+1)%n])
    vertices=[];faces=[]
    for j in range(rows):
        z=waist*(1-j/(rows-1))+.078*j/(rows-1)
        for i in range(n):
            a=2*math.pi*i/n;rad=radii[j*n+i]
            vertices.append(clearance(Vector((center.x+rad*math.cos(a),center.y+rad*math.sin(a),z))))
    for j in range(rows-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=b+n;d=a+n
            faces.extend(((a,c,b),(a,d,c)))
    oldmesh=proxy.data;proxy.data=bpy.data.meshes.new('WitchRebuilt_DrapeRefinement03')
    proxy.data.from_pydata(vertices,[],faces);proxy.data.update()
    for mat in oldmesh.materials:proxy.data.materials.append(mat)
    weights(proxy)
    counts={}
    # The identity meshes were only ~4k triangles each. Refine those contours
    # and exposed hands/feet, rather than subdividing the already dense robe.
    for name in ('Witch_Hat','Witch_Head_Hair','WitchRebuilt_CompleteBody','WitchRebuilt_Lining'):
        obj=bpy.data.objects[name];before=sum(len(p.vertices)-2 for p in obj.data.polygons)
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000025)
        bm.to_mesh(obj.data);bm.free()
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        mod=obj.modifiers.new('SurfaceRefinement','SUBSURF');mod.levels=1;mod.render_levels=1
        mod.boundary_smooth='PRESERVE_CORNERS';bpy.ops.object.modifier_move_up(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        if obj.data.has_custom_normals:obj.data.normals_split_custom_set([(0,0,0)]*len(obj.data.loops))
        counts[name]={'before_triangles':before,'after_triangles':sum(len(p.vertices)-2 for p in obj.data.polygons)}
    for obj in list(bpy.context.scene.objects):
        if obj.type!='MESH' or obj==proxy:continue
        for p in obj.data.polygons:p.use_smooth=True
        # A second, measured UV channel gives cloth/pores consistent density.
        while len(obj.data.uv_layers)<2:obj.data.uv_layers.new(name='DetailUV')
        uv=obj.data.uv_layers[1];tile=.012 if 'Head' in obj.name or 'CompleteBody' in obj.name else .04
        for p in obj.data.polygons:
            axis=max(range(3),key=lambda i:abs(p.normal[i]));axes=[i for i in range(3) if i!=axis]
            for loop in p.loop_indices:
                v=obj.data.vertices[obj.data.loops[loop].vertex_index].co
                uv.data[loop].uv=(v[axes[0]]/tile,v[axes[1]]/tile)
        obj.data.update()
    rig['surface_revision']=REV
    report={'revision':REV,'skirt_vertices_clearance_corrected':sum(x>1e-6 for x in moved),
        'max_local_clearance_adjustment_cm':max(moved)*100,'detail_geometry':counts,
        'skirt_support':'Continuous pelvis/thigh/calf weights, no foot/toe influence',
        'cloth_proxy_vertices':len(vertices),'detail_uv_tile_m':{'fabric':.04,'skin':.012},
        'actor_scale_changed':False}
    OUT.mkdir(exist_ok=True);(OUT/'surface_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

def export(rig):
    proxy=bpy.data.objects['WitchRebuilt_SimulationProxy']
    for include,name in [(False,'SK_WitchRebuilt.fbx'),(True,'SK_WitchRebuilt_ClothBuildSource.fbx')]:
        bpy.ops.object.select_all(action='DESELECT')
        for o in bpy.context.scene.objects:
            if o==rig or (o.type=='MESH' and (o!=proxy or include)):
                o.hide_set(False);o.select_set(True)
        bpy.context.view_layer.objects.active=rig
        bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery'/name),use_selection=True,object_types={'ARMATURE','MESH'},
            add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=False,
            axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',use_mesh_modifiers=True)
    proxy.hide_render=True;proxy.hide_set(True)

if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Before/Authoring/WitchRebuilt_Master.blend'))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    rig.data.pose_position='REST';apply(rig);export(rig)
    rig.data.pose_position='POSE'
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Master.blend'))
    print('Refined garment support, clearance, contours and measured detail UVs')
