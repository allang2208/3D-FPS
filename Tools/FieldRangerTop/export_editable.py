"""Native game exports, editable masters and the production inventory image."""
import gc, importlib.util, json, math
from pathlib import Path
import bpy, numpy as np
from mathutils import Matrix, Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020';OUT=R/'Exports';OUT.mkdir(exist_ok=True)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
rig_io=module('ranger_rig_io','Tools/BlueMageRobe/save_editable.py')
icon_io=module('ranger_icon_io','Tools/ModularOutfit/render_field_sweater_inventory_icons.py')
display_io=module('ranger_display_io','Tools/BlueMageSetIcons/render_icons.py');display_io.OUT=R/'Display';display_io.OUT.mkdir(exist_ok=True)
def mat(name,family=None,color=None,rough=.7,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n['Principled BSDF']
    bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    if color:bs.inputs['Base Color'].default_value=(*color,1)
    if family:
        for channel in ('BaseColor','Normal','ORM'):
            image=bpy.data.images.load(str(R/'Textures'/(family+'_'+channel+'.png')),check_existing=True)
            image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
            t=n.new('ShaderNodeTexImage');t.image=image
            if channel=='BaseColor':l.new(t.outputs['Color'],bs.inputs['Base Color'])
            elif channel=='Normal':
                normal=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
            else:
                split=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],split.inputs[0]);l.new(split.outputs['Green'],bs.inputs['Roughness']);l.new(split.outputs['Blue'],bs.inputs['Metallic'])
        bs.inputs['Sheen Weight'].default_value=.15 if family=='RangerTwill' else 0
    m['UE_Material']='/Game/Characters/ModularOutfit20260924/FieldRangerTop20261020/Materials/M_'+name
    return m
def materials(d):
    a=[mat('RangerCloth','RangerTwill'),mat('RangerLeather','RangerLeather'),mat('RangerLining',color=(.027,.032,.022),rough=.88),
       mat('RangerBrass',color=(.22,.145,.062),rough=.48,metal=.9),mat('RangerThread',color=(.14,.095,.052),rough=.82),
       mat('ExposedTorsoSkin',color=(.30,.18,.12),rough=.65)]
    if len(d['material_slots'])>6:a+=a
    return a
def mesh_for(d,rig):
    mesh=bpy.data.meshes.new(d['profile']+'_FieldRangerTop')
    mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions']],[],d['triangles']);mesh.update()
    ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
    for m in materials(d):mesh.materials.append(m)
    uv=mesh.uv_layers.new(name='Physical8cm')
    for fi,poly in enumerate(mesh.polygons):
        poly.material_index=d['triangle_materials'][fi];poly.use_smooth=True
        for ci,li in enumerate(poly.loop_indices):a,b=d['uv'][fi][ci];uv.data[li].uv=(a,1-b)
    mesh.normals_split_custom_set([(x,-y,z) for face in d['normals'] for x,y,z in face])
    groups={n:ob.vertex_groups.new(name=n) for n in {n for w in d['weights'] for n in w}}
    for i,w in enumerate(d['weights']):
        for name,value in w.items():groups[name].add([i],value,'REPLACE')
    ob.parent=rig;ob.modifiers.new('Native cloth binding','ARMATURE').object=rig;ob['Contract']=d['contract']
    if d['profile'].startswith('Owner'):
        for poly in mesh.polygons:poly.hide=poly.material_index>=6
    return ob
def high_sources():
    collection=bpy.data.collections.new('HIGH_ReliefSources_BakeOnly');bpy.context.scene.collection.children.link(collection)
    collection.hide_render=True;collection.hide_viewport=True
    for family in ('RangerTwill','RangerLeather'):
        h=np.load(R/'Textures'/(family+'_height_cm.npy'))[::4,::4];ny,nx=h.shape
        mesh=bpy.data.meshes.new('HIGH_'+family)
        mesh.from_pydata([(x/(nx-1)*.08,y/(ny-1)*.08,float(h[y,x])*.01) for y in range(ny) for x in range(nx)],[],[(y*nx+x,y*nx+x+1,(y+1)*nx+x+1,(y+1)*nx+x) for y in range(ny-1) for x in range(nx-1)])
        ob=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(ob);ob['Purpose']='Physical relief source for baked PBR; excluded from game FBX'
def main():
    manifest=json.loads((R/'authored.json').read_text());exports=[]
    if not manifest['completed']:raise RuntimeError('Ranger authoring is incomplete')
    for row in manifest['records']:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
        d=json.loads(Path(row['authored']).read_text());rig=rig_io.rig_for(d);ob=mesh_for(d,rig)
        bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);ob.select_set(True);bpy.context.view_layer.objects.active=ob
        fbx=OUT/(row['profile']+'_FieldRangerTop.fbx')
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
        exports.append(str(fbx))
        if row['profile'] in ('Jason','M4','Bow','Body','Owner_Jason'):
            if row['profile']=='Jason':high_sources()
            bpy.ops.file.pack_all();blend=OUT/(row['profile']+'_FieldRangerTop.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend));exports.append(str(blend))
        if row['profile']=='Jason':
            for side,angle in (('l',12.),('r',-12.)):
                bone=rig.pose.bones['upperarm_'+side];h=bone.matrix.translation.copy()
                bone.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(angle),4,'Y')@Matrix.Translation(-h)@bone.matrix
            bpy.context.view_layer.update();scene=icon_io.studio(ob,320,320);scene.cycles.samples=256
            scene.render.filepath=str(R/'ue_field_sweater.png');bpy.ops.render.render(write_still=True)
            display_io.export_display('ue_field_sweater',ob,scene.camera)
            bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FieldRangerTop_Inventory.blend'))
        print('RANGER_EXPORT',row['profile'],flush=True);del d;gc.collect()
    (R/'editable.json').write_text(json.dumps(dict(completed=True,exports=exports,icon=str(R/'ue_field_sweater.png'),
        display=str(R/'Display/ue_field_sweater-display.json'),runtime_tested=False),indent=2),encoding='utf-8')
    print('RANGER_EXPORTS_COMPLETE',len(exports),flush=True)
if __name__=='__main__':main()
