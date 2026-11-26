"""Packed construction source, native skinned FBXs, and a separate displaced high mesh.

No preview rendering and no UE/editor operations.
"""
import gc,importlib.util,json,sys
from pathlib import Path
import bpy,numpy as np
P=Path('D:/FPS3D/FPSGAME');R=Path(globals().get('ROOT_OVERRIDE',P/'SourceAssets/RangerLeatherPants20261021'));OUT=R/'Exports';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def module(name,path):
    s=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
rigio=module('pants_native_rig','Tools/BlueMageRobe/save_editable.py')
def material(name,family=None,color=None,rough=.7,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes['Principled BSDF']
    bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal;bs.inputs['Specular IOR Level'].default_value=.25
    if color:bs.inputs['Base Color'].default_value=(*color,1)
    surface=read(R/'surfaces.json') if (R/'surfaces.json').exists() else {}
    if name=='WaxedThread' and (surface.get('revision')=='AtelierFinishV2' or 'thread_linear_color' in surface):
        thread_color=(*surface.get('thread_linear_color',[.060,.034,.016]),1)
        bs.inputs['Base Color'].default_value=thread_color
        vc=nodes.new('ShaderNodeVertexColor');vc.layer_name='TailoringFinish';mul=nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[1].default_value=thread_color;links.new(vc.outputs['Color'],mul.inputs[2]);links.new(mul.outputs[0],bs.inputs['Base Color']);bs.inputs['Sheen Weight'].default_value=.18
    if family:
        vc=nodes.new('ShaderNodeVertexColor');vc.layer_name='TailoringFinish'
        for channel in ('BaseColor','Normal','ORM'):
            image=bpy.data.images.load(str(R/'Textures'/(family+'_'+channel+'.png')),check_existing=True);image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
            tex=nodes.new('ShaderNodeTexImage');tex.image=image
            if channel=='BaseColor':
                mul=nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;links.new(tex.outputs['Color'],mul.inputs[1]);links.new(vc.outputs['Color'],mul.inputs[2]);links.new(mul.outputs[0],bs.inputs['Base Color'])
            elif channel=='Normal':
                normal=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs[0],bs.inputs['Normal'])
            else:
                split=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],split.inputs[0]);mul=nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';links.new(split.outputs['Green'],mul.inputs[0]);links.new(vc.outputs['Alpha'],mul.inputs[1]);links.new(mul.outputs[0],bs.inputs['Roughness']);links.new(split.outputs['Blue'],bs.inputs['Metallic'])
        if family=='OliveTwill':bs.inputs['Sheen Weight'].default_value=.16
    span=read(R/'surfaces.json').get('tile_cm_by_family',{}).get(family,8)
    m['SurfaceBasis']=str(span)+' cm metric chart; OpenGL normal; same physical height field as HIGH author mesh'
    return m
def make(d,rig,mats):
    mesh=bpy.data.meshes.new('SK_'+d['profile']+'_RangerLeatherPants');mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions']],[],d['triangles']);mesh.update()
    ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
    for mat in mats:mesh.materials.append(mat)
    uv=mesh.uv_layers.new(name='PhysicalMaterialScale')
    for i,poly in enumerate(mesh.polygons):
        poly.material_index=d['triangle_materials'][i];poly.use_smooth=True
        for ci,li in enumerate(poly.loop_indices):u,v=d['uv'][i][ci];uv.data[li].uv=(u,1-v)
    mesh.normals_split_custom_set([(x,-y,z) for face in d['normals'] for x,y,z in face])
    colors=mesh.color_attributes.new(name='TailoringFinish',type='FLOAT_COLOR',domain='POINT');colors.data.foreach_set('color',np.asarray(d['colors'],np.float32).ravel());mesh.color_attributes.active_color=colors
    groups={n:ob.vertex_groups.new(name=n) for n in {n for w in d['weights'] for n in w}}
    for i,weights in enumerate(d['weights']):
        for n,w in weights.items():groups[n].add([i],w,'REPLACE')
    # Named face regions retain editable construction parts without thousands of
    # runtime objects or draw sections for individual stitches.
    attr=mesh.attributes.new('TailoringPart',type='INT',domain='FACE');part_ids=np.empty(len(mesh.polygons),np.int32)
    for i,part in enumerate(d['parts']):part_ids[part['first_triangle']:part['first_triangle']+part['triangles']]=i
    attr.data.foreach_set('value',part_ids);ob['TailoringParts']=json.dumps(d['parts']);ob['Concept']=d.get('concept','Design/LeatherPants_Concept02.png');ob['Contract']=d['contract'];ob['SourceJSON']=str(R/'Authored/ue_leather_pants'/(d['profile']+'.json'))
    ob.parent=rig;ob.modifiers.new('NativeJasonSkin','ARMATURE').object=rig;return ob

def export_fbx(ob,rig,path):
    """Use an interchange graph that FBX can actually serialize."""
    original=list(ob.data.materials);temporary=[]
    for i,m in enumerate(original):
        if i>=3:temporary.append(m);continue
        family=('WalnutLeather','ReinforcedLeather','OliveTwill')[i];mat=m.copy();mat.name=m.name+'_FBX';ns=mat.node_tree.nodes;links=mat.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
        base=next(n for n in ns if n.type=='TEX_IMAGE' and n.image and n.image.filepath.endswith(family+'_BaseColor.png'))
        for link in list(bs.inputs['Base Color'].links):links.remove(link)
        links.new(base.outputs['Color'],bs.inputs['Base Color'])
        for link in list(bs.inputs['Roughness'].links):links.remove(link)
        rough=ns.new('ShaderNodeTexImage');rough.image=bpy.data.images.load(str(R/'Textures/Exchange'/(family+'_Roughness.png')),check_existing=True);rough.image.colorspace_settings.name='Non-Color';links.new(rough.outputs['Color'],bs.inputs['Roughness'])
        for link in list(bs.inputs['Metallic'].links):links.remove(link)
        bs.inputs['Metallic'].default_value=0.;temporary.append(mat)
    try:
        for i,m in enumerate(temporary):ob.data.materials[i]=m
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',path_mode='RELATIVE')
    finally:
        for i,m in enumerate(original):ob.data.materials[i]=m
        for m in temporary[:3]:bpy.data.materials.remove(m)

def high_source(ob):
    hi=ob.copy();hi.data=ob.data.copy();hi.name='HIGH_LeatherPants_PhysicalRelief';bpy.context.collection.objects.link(hi)
    for m in list(hi.modifiers):hi.modifiers.remove(m)
    bpy.context.view_layer.objects.active=hi;bpy.ops.object.select_all(action='DESELECT');hi.select_set(True)
    sub=hi.modifiers.new('SurfaceFieldResolution','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
    mesh=hi.data;count=len(mesh.vertices);coords=np.empty(count*3,np.float32);mesh.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
    ns=np.empty(count*3,np.float32);mesh.vertices.foreach_get('normal',ns);ns=ns.reshape(-1,3);heights=np.zeros(count);samples=np.zeros(count)
    fields=[np.load(R/'Textures'/(family+'_height_cm.npy')) for family in ('WalnutLeather','ReinforcedLeather','OliveTwill')]
    uvs=np.empty(len(mesh.loops)*2,np.float32);mesh.uv_layers.active.data.foreach_get('uv',uvs);uvs=uvs.reshape(-1,2)
    vertices=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',vertices)
    starts=np.empty(len(mesh.polygons),np.int32);totals=np.empty_like(starts);slots=np.empty_like(starts);mesh.polygons.foreach_get('loop_start',starts);mesh.polygons.foreach_get('loop_total',totals);mesh.polygons.foreach_get('material_index',slots)
    loopslots=np.repeat(slots,totals)
    for slot,field in enumerate(fields):
        mask=loopslots==slot;uv=uvs[mask];x=np.mod(uv[:,0],1)*field.shape[1];y=np.mod(1-uv[:,1],1)*field.shape[0];x0=np.floor(x).astype(int)%field.shape[1];y0=np.floor(y).astype(int)%field.shape[0];dx=x-np.floor(x);dy=y-np.floor(y)
        h=(field[y0,x0]*(1-dx)*(1-dy)+field[y0,(x0+1)%field.shape[1]]*dx*(1-dy)+field[(y0+1)%field.shape[0],x0]*(1-dx)*dy+field[(y0+1)%field.shape[0],(x0+1)%field.shape[1]]*dx*dy)*.01
        np.add.at(heights,vertices[mask],h);np.add.at(samples,vertices[mask],1)
    coords+=ns*(heights/np.maximum(samples,1))[:,None];mesh.vertices.foreach_set('co',coords.ravel());mesh.update()
    # Zero custom vectors request automatic normals on the displaced HIGH mesh;
    # the game's original authored split normals remain on its separate mesh.
    mesh.normals_split_custom_set([(0.,0.,0.)]*len(mesh.loops));mesh.update()
    # HIGH geometry already has relief: remove its normal-map link to avoid
    # displaying the same physical grain twice when opened for sculpting.
    for i,mat in enumerate(mesh.materials):
        m=mat.copy();m.name='HIGH_'+mat.name;bs=m.node_tree.nodes.get('Principled BSDF')
        for link in list(bs.inputs['Normal'].links):m.node_tree.links.remove(link)
        mesh.materials[i]=m
    hi['BakeOnly']=True;hi['Source']='Explicit leather/twill height fields, centimetres';hi['GameExport']=False
    collection=bpy.data.collections.new('HIGH_BakeOnly_NotForGameExport');bpy.context.scene.collection.children.link(collection)
    for c in list(hi.users_collection):c.objects.unlink(hi)
    collection.objects.link(hi);collection.hide_render=True;collection.hide_viewport=True
    return dict(vertices=count,polygons=len(mesh.polygons),triangles=sum(len(p.vertices)-2 for p in mesh.polygons),object=hi.name)

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    mats=[material('WalnutLeather','WalnutLeather'),material('ReinforcedLeather','ReinforcedLeather'),material('OliveTwill','OliveTwill'),material('DarkLining',color=(.018,.016,.012),rough=.9),material('WaxedThread',color=(.12,.075,.038),rough=.84),material('AgedSteel',color=(.17,.18,.19),rough=.46,metal=1)]
    rigs=[];objects=[];exports=[];standard=None;counts=[]
    for profile in ('Jason','Jason_ShortBootsFit','Jason_HighBootsFit'):
        d=read(R/'Authored/ue_leather_pants'/(profile+'.json'));rig=rigio.rig_for(d);ob=make(d,rig,mats);rigs.append(rig);objects.append(ob)
        bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
        fbx=OUT/(profile+'_RangerLeatherPants.fbx');export_fbx(ob,rig,fbx);exports.append(str(fbx))
        if profile=='Jason':standard=ob
        else:ob.hide_set(True);ob.hide_render=True;rig.hide_set(True);rig.hide_render=True
        counts.append(dict(profile=profile,vertices=len(d['positions']),triangles=len(d['triangles'])));print('RANGER_PANTS_EXPORTED',profile,flush=True);del d;gc.collect()
    high=high_source(standard)
    # Separate source tiles retain the exact scalar field used by the PBR baker.
    c=bpy.data.collections.new('HIGH_PhysicalMaterialSwatches');bpy.context.scene.collection.children.link(c);c.hide_viewport=True;c.hide_render=True
    surface=read(R/'surfaces.json')
    for fi,family in enumerate(('WalnutLeather','ReinforcedLeather','OliveTwill')):
        span=surface.get('tile_cm_by_family',{}).get(family,8);h=np.load(R/'Textures'/(family+'_height_cm.npy'))[::4,::4];ny,nx=h.shape;mesh=bpy.data.meshes.new('HIGH_'+family+'_'+str(span)+'cm')
        mesh.from_pydata([(x/(nx-1)*span*.01+fi*.30,y/(ny-1)*span*.01,float(h[y,x])*.01) for y in range(ny) for x in range(nx)],[],[(y*nx+x,y*nx+x+1,(y+1)*nx+x+1,(y+1)*nx+x) for y in range(ny-1) for x in range(nx-1)]);tile=bpy.data.objects.new(mesh.name,mesh);c.objects.link(tile);tile['BakeOnly']=True;tile['PhysicalSpanCM']=span
    bpy.ops.object.select_all(action='DESELECT');standard.select_set(True);bpy.context.view_layer.objects.active=standard
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene['Concept']=surface.get('concept','Approved LeatherPants_Concept02');bpy.context.scene['GameTested']=False
    bpy.ops.file.pack_all();blend=R/'RangerLeatherPants_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    receipt=dict(completed=True,blend=str(blend),exports=exports,models=counts,high=high,texture_families=3,texture_maps=9,texture_size=surface.get('resolution_by_family',2048),surface_revision=surface.get('revision'),preview_rendered=False,ue_imported=False,runtime_tested=False)
    (R/'delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('RANGER_PANTS_MODEL_DELIVERED',json.dumps(receipt),flush=True)
if __name__=='__main__':main()
