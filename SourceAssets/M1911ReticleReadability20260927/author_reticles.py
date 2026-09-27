"""Separate compact-pistol reticle size from the already fitted optical body."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent;E=O/'Exports';E.mkdir(exist_ok=True)
base=S/'M1911AttachmentPolish20260927';previous=json.loads((base/'optics_authoring.json').read_text())
bpy.context.preferences.filepaths.save_version=0;records={}
for key,factor in [('holographic',2.5),('panoramic_red_dot',2.)]:
    source=base/('M1911_'+key+'_RoundedMount_Editable.blend');bpy.ops.wm.open_mainfile(filepath=str(source))
    ob=bpy.data.objects['SM_M1911_'+key+'_Rounded20260927'];me=ob.data
    slot=next(i for i,m in enumerate(me.materials) if m and 'Reticle' in m.name)
    reticle={i for p in me.polygons if p.material_index==slot for i in p.vertices}
    aim=Vector(previous[key]['aim_local_m']);normals=[n.vector.copy() for n in me.corner_normals]
    coords=[me.vertices[i].co.copy() for i in reticle]
    before=[max(p[i] for p in coords)-min(p[i] for p in coords) for i in range(3)]
    for i in reticle:
        p=me.vertices[i].co;p.y=aim.y+(p.y-aim.y)*factor;p.z=aim.z+(p.z-aim.z)*factor
    for li,loop in enumerate(me.loops):
        if loop.vertex_index in reticle:normals[li].y/=factor;normals[li].z/=factor;normals[li].normalize()
    me.update();me.normals_split_custom_set(normals)
    ob.name='SM_M1911_'+key+'_ReadableReticle20260927';ob.hide_set(False);ob.hide_render=False
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    for child in ob.children:
        if child.type=='EMPTY':child.select_set(True)
    fbx=E/(ob.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',
       bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/('M1911_'+key+'_ReadableReticle_Editable.blend')))
    records[key]={**previous[key],'source':str(source),'fbx':str(fbx),'factor_from_polished_version':factor,
        'reticle_size_before_m':before,'reticle_size_after_m':[before[0],before[1]*factor,before[2]*factor],
        'changed_vertices':len(reticle),'method':'Reticle-only Y/Z scaling about original optical center; original X depth, mount, body, UV, material and sockets retained',
        'game_tested':False}
(O/'optics_authoring.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('M1911_READABLE_RETICLES_AUTHORED',flush=True)
