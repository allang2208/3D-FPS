"""Native-rig production sources, game FBX exports and the inventory icon."""
import json,math,gc,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'Exports';OUT.mkdir(exist_ok=True)
def material(name,kind='fabric'):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF']
    if kind in ('silver','gem'):
        p.inputs['Base Color'].default_value=(.48,.46,.40,1) if kind=='silver' else (.012,.08,.45,1);p.inputs['Metallic'].default_value=1 if kind=='silver' else .45;p.inputs['Roughness'].default_value=.34 if kind=='silver' else .10;return m
    uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=(1,1,1) if kind in ('embroidery','skirt') else (6.25,6.25,1);l.new(uv.outputs['UV'],scale.inputs[0])
    family='BlueMageEmbroidery' if kind=='embroidery' else 'BlueMageSkirtDisplay' if kind=='skirt' else 'BlueMageFabric'
    for channel in ('BaseColor','Normal','ORM'):
        image=bpy.data.images.load(str(R/'Textures'/('T_'+family+'_'+channel+'.png')),check_existing=True)
        if channel!='BaseColor':image.colorspace_settings.name='Non-Color'
        t=n.new('ShaderNodeTexImage');t.image=image;l.new(scale.outputs[0],t.inputs['Vector'])
        if channel=='BaseColor':
            if kind in ('lining','hood','belt'):
                mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*({'lining':(.40,.43,.52),'hood':(.85,.85,.85),'belt':(.22,.27,.34)}[kind]),1);l.new(t.outputs['Color'],mix.inputs[1]);l.new(mix.outputs[0],p.inputs['Base Color'])
            else:l.new(t.outputs['Color'],p.inputs['Base Color'])
        elif channel=='Normal':
            normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.25 if kind=='belt' else .65 if kind=='lining' else 1;l.new(t.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],p.inputs['Normal'])
        else:
            split=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],split.inputs[0]);l.new(split.outputs['Green'],p.inputs['Roughness']);l.new(split.outputs['Blue'],p.inputs['Metallic'])
    m['UE_PBR']='Source physical height fields; OpenGL tangent normal; UE import flips green';return m
def materials():return [material('RobeBody'),material('RobeSleeves'),material('RobeCuffs','embroidery'),material('SleeveLining','lining'),material('RobeSkirt','skirt'),material('RobeHood','hood'),material('RobeEmbroidery','embroidery'),material('RobeBelt','belt'),material('RobeSilver','silver'),material('RobeSimulationProxy','lining'),material('TorsoLining','lining'),material('RobeGem','gem')]
def rig_for(d):
    bones=d['bones'];ordered=sorted(bones,key=lambda n:bones[n]['index']);byid={b['index']:n for n,b in bones.items()};reflection=Matrix.Diagonal((1,-1,1));arm=bpy.data.armatures.new(d['profile']+'_NativeRig');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for name in ordered:
        b=bones[name];bone=arm.edit_bones.new(name);axes=Matrix(b['axes']).transposed()
        for i in range(3):axes.col[i]=axes.col[i].normalized()
        matrix=(reflection@axes@reflection).to_4x4();matrix.translation=reflection@Vector(b['position'])*.01;bone.matrix=matrix;bone.length=.025
    for name in ordered:
        if bones[name]['parent']>=0:arm.edit_bones[name].parent=arm.edit_bones[byid[bones[name]['parent']]]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False);return rig
def mesh_for(d,rig,mats,proxy=False):
    chosen=[i for i,slot in enumerate(d['triangle_materials']) if (slot==9)==proxy];used=sorted({v for i in chosen for v in d['triangles'][i]});remap={v:i for i,v in enumerate(used)};name=d['profile']+('_SimulationProxy' if proxy else '_BlueMageRobe');mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([(d['positions'][i][0]*.01,-d['positions'][i][1]*.01,d['positions'][i][2]*.01) for i in used],[],[[remap[v] for v in d['triangles'][i]] for i in chosen]);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    for m in mats:mesh.materials.append(m)
    uv=mesh.uv_layers.new(name='PhysicalGarmentUV')
    for poly,fi in zip(mesh.polygons,chosen):
        poly.material_index=d['triangle_materials'][fi];poly.use_smooth=True
        for ci,li in enumerate(poly.loop_indices):a,b=d['uv'][fi][ci];uv.data[li].uv=(a,1-b)
    mesh.normals_split_custom_set([(x,-y,z) for fi in chosen for x,y,z in d['normals'][fi]])
    groups={n:ob.vertex_groups.new(name=n) for n in {n for i in used for n in d['weights'][i]}}
    for vi,src in enumerate(used):
        for name,w in d['weights'][src].items():groups[name].add([vi],w,'REPLACE')
    ob.parent=rig;ob.modifiers.new('Native garment skinning','ARMATURE').object=rig;ob['SourceContract']=d['contract'];ob['SourceBinding']=d['binding_source'];return ob
def high_sources():
    collection=bpy.data.collections.new('HIGH_BakeSources_ExcludeFromGame');bpy.context.scene.collection.children.link(collection);collection.hide_render=True;collection.hide_viewport=True
    for family,span,stride in [('BlueMageFabric',(4.,4.),4),('BlueMageEmbroidery',(22.,3.5),4)]:
        h=np.load(R/'Textures'/(family+'_height_cm.npy'))[::stride,::stride];ny,nx=h.shape;mesh=bpy.data.meshes.new('HIGH_'+family)
        mesh.from_pydata([(x/(nx-1)*span[0]*.01,y/(ny-1)*span[1]*.01,float(h[y,x])*.01) for y in range(ny) for x in range(nx)],[],[(y*nx+x,y*nx+x+1,(y+1)*nx+x+1,(y+1)*nx+x) for y in range(ny-1) for x in range(nx-1)])
        ob=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(ob);ob['Usage']='Actual physical relief source used for shared PBR maps; bake only'
def icon(ob):
    import sys
    sys.path.insert(0,str(P/'Tools/BlueMageSetIcons'))
    from render_icons import render_current
    return render_current('ue_blue_mage_robe',ob)

def main():
    files=[R/'Authored/Body/Jason.json']+sorted((R/'Authored/Body').glob('*.json'))+sorted((R/'Authored/FP').glob('*.json'));done=set();exports=[]
    if '--body-only' in sys.argv:files=[f for f in files if f.parent.name=='Body']
    for file in files:
        if file in done:continue
        done.add(file);bpy.ops.wm.read_factory_settings(use_empty=True);d=json.loads(file.read_text());mats=materials();rig=rig_for(d);ob=mesh_for(d,rig,mats);bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
        fbx=OUT/(file.stem+'_BlueMageRobe.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE');exports.append(str(fbx))
        if file.parent.name=='Body':
            proxy=mesh_for(d,rig,mats,True);proxy.hide_render=True;proxy.hide_set(True);proxy['Usage']='UE Chaos simulation input; excluded from visible FBX export'
        if file.stem=='Jason':high_sources()
        bpy.ops.file.pack_all();blend=OUT/(file.stem+'_BlueMageRobe.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        if file.stem=='Jason':icon(ob)
        print('BLUE_ROBE_EDITABLE_SAVED',file.stem,flush=True);del d;gc.collect()
    if '--body-only' in sys.argv and (R/'editable_receipt.json').exists():exports=list(dict.fromkeys(json.loads((R/'editable_receipt.json').read_text()).get('exports',[])+exports))
    (R/'editable_receipt.json').write_text(json.dumps(dict(exports=exports,production_icon=str(R/'ue_blue_mage_robe.png'),runtime_tested=False),indent=2),encoding='utf-8');print('BLUE_ROBE_EDITABLE_COMPLETE',len(exports),flush=True)
if __name__=='__main__':main()
