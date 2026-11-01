"""Bake the original bolt UVs with a restrained 2-over-2 carbon weave, no geometry edits."""
import bpy,math,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).resolve().parent;T=O/'Textures';T.mkdir(exist_ok=True)
source=O.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];r.animation_data_clear()
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
s.frame_set(0);bpy.context.view_layer.update()
bolts=[bpy.data.objects[n] for n in ('M24_bolt','M24_boltrear')]
body=[o for o in s.objects if o.type=='MESH' and any(m and m.name.startswith('M24_Body') for m in o.data.materials)]
for o in bolts:
    if o not in body:body.append(o)
image=bpy.data.images.new('T_M24_CarbonWeaveMask',width=2048,height=2048,alpha=True)
image.colorspace_settings.name='Non-Color';image.generated_color=(0,0,0,1)
def material(ob,carbon):
    m=bpy.data.materials.new('Carbon map '+ob.name+(' body' if carbon else ' steel'));m.use_nodes=True
    n=m.node_tree.nodes;n.clear();l=m.node_tree.links
    def mathnode(op,a,b=None):
        z=n.new('ShaderNodeMath');z.operation=op
        for i,v in enumerate((a,b)):
            if v is None:continue
            if isinstance(v,(float,int)):z.inputs[i].default_value=v
            else:l.new(v,z.inputs[i])
        return z.outputs[0]
    rgb=n.new('ShaderNodeCombineColor');rgb.mode='RGB';rgb.inputs[0].default_value=1 if carbon else 0
    if carbon:
        tex=n.new('ShaderNodeTexCoord');tex.object=r
        sep=n.new('ShaderNodeSeparateXYZ');l.new(tex.outputs['Object'],sep.inputs[0]);x,y,z=sep.outputs
        pts=[ob.matrix_world@v.co for v in ob.data.vertices]
        cx=(min(p.x for p in pts)+max(p.x for p in pts))*.5;cz=(min(p.z for p in pts)+max(p.z for p in pts))*.5
        around=mathnode('MULTIPLY',mathnode('ARCTAN2',mathnode('SUBTRACT',z,cz),mathnode('SUBTRACT',x,cx)),.009)
        a=mathnode('MULTIPLY',mathnode('ADD',y,around),360/math.sqrt(2))
        b=mathnode('MULTIPLY',mathnode('SUBTRACT',y,around),360/math.sqrt(2))
        top=mathnode('LESS_THAN',mathnode('FLOORED_MODULO',mathnode('ADD',mathnode('FLOOR',a),mathnode('FLOOR',b)),4),2)
        lane=mathnode('ADD',mathnode('MULTIPLY',a,top),mathnode('MULTIPLY',b,mathnode('SUBTRACT',1,top)))
        crown=mathnode('MULTIPLY',mathnode('COSINE',mathnode('MULTIPLY',lane,2*math.pi)),.5)
        # Cosine shifted to [0,1], then subtle fiber sub-bands inside each tow.
        crown=mathnode('ADD',crown,.5)
        fiber=mathnode('ADD',.5,mathnode('MULTIPLY',mathnode('COSINE',mathnode('MULTIPLY',lane,2*math.pi*9)),.5))
        shade=mathnode('ADD',mathnode('MULTIPLY',crown,.80),mathnode('MULTIPLY',fiber,.20))
        l.new(shade,rgb.inputs[1]);l.new(top,rgb.inputs[2])
    emit=n.new('ShaderNodeEmission');l.new(rgb.outputs[0],emit.inputs['Color'])
    out=n.new('ShaderNodeOutputMaterial');l.new(emit.outputs[0],out.inputs[0])
    target=n.new('ShaderNodeTexImage');target.image=image;n.active=target
    return m
bpy.ops.object.select_all(action='DESELECT');records=[]
for ob in body:
    ob.hide_set(False);ob.hide_render=False;ob.select_set(True)
    ob.data=ob.data.copy();ob.data.materials.clear();ob.data.materials.append(material(ob,False))
    if ob in bolts:
        ob.data.materials.append(material(ob,True))
        ys=[(ob.matrix_world@v.co).y for v in ob.data.vertices];lo,hi=min(ys),max(ys)
        for p in ob.data.polygons:
            y=sum((ob.matrix_world@ob.data.vertices[i].co).y for i in p.vertices)/len(p.vertices)
            # Preserve the original metal end faces and contact collars.
            p.material_index=int(lo+(hi-lo)*.065<y<hi-(hi-lo)*.055)
        records.append({'object':ob.name,'carbon_faces':sum(p.material_index==1 for p in ob.data.polygons),'faces':len(ob.data.polygons)})
bpy.context.view_layer.objects.active=bolts[0]
s.render.engine='CYCLES';s.cycles.samples=1;s.render.bake.margin=6;s.render.bake.use_selected_to_active=False
bpy.ops.object.bake(type='EMIT',use_clear=True)
image.filepath_raw=str(T/(image.name+'.png'));image.file_format='PNG';image.save()
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_CarbonBolt_Surface_Editable.blend'))
(O/'surface_recipe.json').write_text(json.dumps({'source':str(source),'objects':records,'map':str(image.filepath_raw),
 'channels':{'R':'carbon region only','G':'tow crown and fiber relief','B':'warp/weft direction'},'weave':'2-over-2 diagonal twill',
 'repeat_metres':1/360,'preserved':'native UV0, normals, geometry, skin, skeleton and actions','runtime_tested':False},indent=2))
print('M24_CARBON_WEAVE_AUTHORED',records,flush=True)
