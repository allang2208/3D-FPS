"""Build one bounded mesh with three smooth shells; all start at the true front."""
import bpy,json,math
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/PsychicWaveV02')
bpy.ops.wm.read_factory_settings(use_empty=True)
verts=[];faces=[];uvs=[];layers=[]
for layer,segments,rows in ((0.,96,48),(.5,64,32),(1.,64,32)):
    start=len(verts)
    for row in range(rows+1):
        theta=math.pi*row/rows
        for col in range(segments+1):
            phi=math.tau*col/segments
            verts.append((math.sin(theta)*math.cos(phi),math.sin(theta)*math.sin(phi),math.cos(theta)))
            uvs.append((col/segments,1-row/rows));layers.append(layer)
    for row in range(rows):
        for col in range(segments):
            a=start+row*(segments+1)+col
            if row==0:faces.append((a,a+segments+1,a+segments+2))
            elif row==rows-1:faces.append((a,a+segments+1,a+1))
            else:faces.append((a,a+segments+1,a+segments+2,a+1))
mesh=bpy.data.meshes.new('HeQuePsychicFrontV02');mesh.from_pydata(verts,[],faces);mesh.update()
uv=mesh.uv_layers.new(name='FlowUV');color=mesh.color_attributes.new(name='WaveLayer',type='FLOAT_COLOR',domain='CORNER')
mesh.color_attributes.active_color=color
for poly in mesh.polygons:
    poly.use_smooth=True
    for index in poly.loop_indices:
        vertex=mesh.loops[index].vertex_index;uv.data[index].uv=uvs[vertex]
        # Binary channels survive FBX colour-space conversion without moving a
        # layer across a floating-point threshold: 00 front, 10 flow, 11 wake.
        color.data[index].color=(float(layers[vertex]>=.5),float(layers[vertex]>=1.),0,1)
obj=bpy.data.objects.new('SM_HeQue_PsychicFrontV02',mesh);bpy.context.collection.objects.link(obj)
obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/SM_HeQue_PsychicFrontV02.fbx'),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE',colors_type='LINEAR')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_PsychicFront_v02.blend'))
report=json.loads((ROOT/'Records/authoring.json').read_text('utf8'))
report.update(vertices=len(verts),triangles=sum(len(f)-2 for f in faces),mesh_radius_cm=100,
    shape='three smooth shells; binary vertex RG = 00 front, 10 flow, 11 wake',
    fixed_components=3,layer_offsets='material WPO, capped during birth; constant centimetres as radius grows')
(ROOT/'Records/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HEQUE_PSYCHIC_FRONT_AUTHORED '+json.dumps(report),flush=True)
