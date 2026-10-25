"""Editable native masters, body FBXs and empty-jacket production icon."""
import copy,gc,sys
import bpy,numpy as np
from mathutils import Matrix
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/WorkwearSet')
from workwear_common import *
sys.path.insert(0,str(P/'Tools/FieldRangerTop'))
import export_editable as io
from workwear_inventory import studio
io.R=R
def materials(d):
    mats=[]
    for family in ('Canvas','Leather','Lining','Brass','Thread'):
        m=bpy.data.materials.new('Workwear_'+family);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n['Principled BSDF']
        for channel in ('BaseColor','Normal','ORM'):
            im=bpy.data.images.load(str(R/'Textures'/f'T_Workwear_{family}_{channel}.png'),check_existing=True);im.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';tex=n.new('ShaderNodeTexImage');tex.image=im
            if channel=='BaseColor':l.new(tex.outputs['Color'],bs.inputs['Base Color'])
            elif channel=='Normal':
                normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
            else:
                sep=n.new('ShaderNodeSeparateColor');l.new(tex.outputs['Color'],sep.inputs[0]);l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
        if family in ('Canvas','Lining','Thread'):bs.inputs['Sheen Weight'].default_value=.10
        m['UE_Material']=DEST+'/Materials/M_Workwear_'+family;mats.append(m)
    mats.append(mats[2]);return mats*2 if len(d['material_slots'])>6 else mats
io.materials=materials
manifest=read(R/'authored.json');female=read(R/'female-authored.json');rows=manifest['records']+female['records'];exports=[]
for row in rows:
    if row.get('owner') or row.get('group')!=manifest['default_group']:continue
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    d=read(row['file']);rig=io.rig_io.rig_for(d);ob=io.mesh_for(d,rig);bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
    path=R/'Exports'/(row['rig']+'_WorkJacket.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE');exports.append(str(path))
    if row['rig']=='Jason':
        high=bpy.data.collections.new('HIGH_BakeOnly_SurfaceFields');bpy.context.scene.collection.children.link(high);high.hide_render=True;high.hide_viewport=True
        for family in ('Canvas','Leather','Lining','Brass','Thread'):
            data=np.load(R/'Exports'/f'HIGH_{family}.npz');h=data['height_cm'][::16,::16];ny,nx=h.shape;span=float(data['span_cm'])*.01;mesh=bpy.data.meshes.new('HIGH_'+family);mesh.from_pydata([(x/(nx-1)*span,y/(ny-1)*span,float(h[y,x])*.01) for y in range(ny) for x in range(nx)],[],[(y*nx+x,y*nx+x+1,(y+1)*nx+x+1,(y+1)*nx+x) for y in range(ny-1) for x in range(nx-1)]);high.objects.link(bpy.data.objects.new(mesh.name,mesh))
    bpy.ops.file.pack_all();path=R/'Exports'/(row['rig']+'_WorkJacket.blend');bpy.ops.wm.save_as_mainfile(filepath=str(path));exports.append(str(path))
    if row['rig']=='Jason':
        # Empty clothing only: skin geometry must not appear in inventory or drops.
        empty=copy.deepcopy(d);chosen=[i for i,s in enumerate(d['triangle_materials']) if s!=5]
        for k in ('triangles','normals','uv','triangle_materials'):empty[k]=[d[k][i] for i in chosen]
        used=sorted({i for f in empty['triangles'] for i in f});remap={i:j for j,i in enumerate(used)}
        for k in ('positions','weights'):empty[k]=[empty[k][i] for i in used]
        empty['triangles']=[[remap[i] for i in f] for f in empty['triangles']];compact(R/'jacket-garment.json',empty)
        ob.hide_render=True;ob.hide_set(True);display=io.mesh_for(empty,rig)
        for side,angle in (('l',12.),('r',-12.)):
            bone=rig.pose.bones['upperarm_'+side];h=bone.matrix.translation.copy();bone.matrix=Matrix.Translation(h)@Matrix.Rotation(np.radians(angle),4,'Y')@Matrix.Translation(-h)@bone.matrix
        bpy.context.view_layer.update();icons=studio(R,KEY);icons.render_current(KEY,display,item=dict(grid_w=3,grid_h=3),camera_offset=(.3,-3,.12))
    print('WORK_JACKET_EXPORT',row['rig'],flush=True);del d;gc.collect()
write(R/'editable.json',dict(completed=True,exports=exports,icon=str(R/(KEY+'.png')),display=str(R/(KEY+'-display.json')),runtime_tested=False))
