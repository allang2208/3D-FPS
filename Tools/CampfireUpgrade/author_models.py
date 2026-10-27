"""Author meat cuts on the existing food grip envelope and bake production PBR/icon assets."""
from pathlib import Path
import bpy, json, math
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/CampfireUpgrade20261026'
ROWS=json.loads((OUT/'foods.json').read_text(encoding='utf-8'))
SOURCE=ROOT/'SourceAssets/Sausage20261014/RoastedSausage_Editable.blend'
for folder in ('Export','Maps','Icons','Blends'): (OUT/folder).mkdir(parents=True,exist_ok=True)

def material(row,cooked):
    m=bpy.data.materials.new('MeatSurface');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bs.inputs['Metallic'].default_value=0;bs.inputs['Specular IOR Level'].default_value=.28
    tc=n.new('ShaderNodeTexCoord');stretch=n.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';l.new(tc.outputs['Generated'],stretch.inputs[0]);stretch.inputs[1].default_value=(3,95,75)
    fibers=n.new('ShaderNodeTexNoise');fibers.inputs['Scale'].default_value=1;fibers.inputs['Detail'].default_value=3;l.new(stretch.outputs[0],fibers.inputs['Vector'])
    coarse=n.new('ShaderNodeTexNoise');coarse.inputs['Scale'].default_value=6;coarse.inputs['Detail'].default_value=4;l.new(tc.outputs['Generated'],coarse.inputs['Vector'])
    tone=n.new('ShaderNodeValToRGB');l.new(coarse.outputs['Fac'],tone.inputs[0])
    low=[x*.4 for x in row['color']] if not cooked else [.055,.017,.006]
    high=[x*1.5 for x in row['color']] if not cooked else [.25,.092,.025]
    tone.color_ramp.elements[0].position=.2;tone.color_ramp.elements[0].color=(*low,1)
    tone.color_ramp.elements[1].position=.78;tone.color_ramp.elements[1].color=(*high,1)
    striations=n.new('ShaderNodeMixRGB');striations.blend_type='MULTIPLY';striations.inputs[0].default_value=.32;l.new(tone.outputs[0],striations.inputs[1]);l.new(fibers.outputs['Fac'],striations.inputs[2])
    veins=n.new('ShaderNodeTexVoronoi');veins.feature='DISTANCE_TO_EDGE';veins.inputs['Scale'].default_value=7;l.new(tc.outputs['Generated'],veins.inputs['Vector'])
    mask=n.new('ShaderNodeMapRange');mask.inputs['From Min'].default_value=.015;mask.inputs['From Max'].default_value=.065
    mask.inputs['To Min'].default_value=row['fat']*(.35 if cooked else 1);mask.inputs['To Max'].default_value=0;l.new(veins.outputs['Distance'],mask.inputs['Value'])
    fat=n.new('ShaderNodeMixRGB');l.new(mask.outputs[0],fat.inputs[0]);l.new(striations.outputs[0],fat.inputs[1]);fat.inputs[2].default_value=(.5,.29,.12,1) if cooked else (.78,.56,.40,1)
    rough=n.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.38 if cooked else .31;rough.inputs['To Max'].default_value=.67 if cooked else .48;l.new(coarse.outputs['Fac'],rough.inputs['Value'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.00017;l.new(fibers.outputs['Fac'],bump.inputs['Height'])
    l.new(fat.outputs[0],bs.inputs['Base Color']);l.new(rough.outputs[0],bs.inputs['Roughness']);l.new(bump.outputs[0],bs.inputs['Normal'])
    return m,bs,out,fat.outputs[0],rough.outputs[0]

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
records=[]
for row in ROWS:
  for state in ('Raw','Roasted'):
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=bpy.context.scene
    obj=next(o for o in scene.objects if o.type=='MESH')
    for o in list(scene.objects):
        if o!=obj:bpy.data.objects.remove(o,do_unlink=True)
    matrix=obj.matrix_world.copy();obj.parent=None;obj.matrix_world=matrix
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    # Exact established body-grip (x>=2cm) and bite tip (x<=-7.8cm) stay intact.
    # Flatten and widen only the exposed cut. This keeps native V7 grasp and bite motion reusable.
    for v in obj.data.vertices:
        x,y,z=v.co;t=max(0.,min(1.,(x+.078)/.018))*max(0.,min(1.,(.02-x)/.022));t=t*t*(3-2*t)
        v.co.y*=1+(row['width']-1)*t
        v.co.z=.0012+(z-.0012)*(1+(row['depth']-1)*t)
        v.co.z+=.0012*t*math.sin(x*160+row['width'])*math.sin(y*210)
    obj.data.update();name=f'SM_{state}{row["key"]}';obj.name=name;obj.data.name=name
    mat,bs,out,color,rough=material(row,state=='Roasted');obj.data.materials.clear();obj.data.materials.append(mat)
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.bake.margin=12;scene.render.bake.use_clear=True
    maps={};nodes=mat.node_tree.nodes;links=mat.node_tree.links
    emit=nodes.new('ShaderNodeEmission')
    for suffix,source in [('BaseColor',color),('Roughness',rough),('NormalGL',None)]:
        im=bpy.data.images.new(f'T_{state}{row["key"]}_{suffix}',width=1024,height=1024,alpha=False)
        if suffix!='BaseColor':im.colorspace_settings.name='Non-Color'
        tex=nodes.new('ShaderNodeTexImage');tex.image=im;nodes.active=tex
        if source:
            links.new(source,emit.inputs['Color']);links.new(emit.outputs[0],out.inputs['Surface']);bpy.ops.object.bake(type='EMIT')
        else:
            links.new(bs.outputs[0],out.inputs['Surface']);bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT')
        im.filepath_raw=str(OUT/'Maps'/f'{im.name}.png');im.file_format='PNG';im.save();maps[suffix]=im
    links.new(bs.outputs[0],out.inputs['Surface'])
    # Export only the authored prop. FBX retains the same (x,-y,z) cm frame as the approved food motion.
    bpy.ops.export_scene.fbx(filepath=str(OUT/'Export'/f'{name}.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False)
    # Production icons, not gameplay or acceptance renders.
    scene.cycles.samples=48;scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
    scene.world=bpy.data.worlds.new('NeutralFoodStudio');scene.world.use_nodes=True
    wn=scene.world.node_tree.nodes;wn.clear();bg=wn.new('ShaderNodeBackground');wo=wn.new('ShaderNodeOutputWorld');bg.inputs['Strength'].default_value=.3;scene.world.node_tree.links.new(bg.outputs[0],wo.inputs['Surface'])
    for light,loc,power,size in [('Key',(-.15,-.20,.35),5,.25),('Fill',(.18,.12,.2),2,.2),('Rim',(-.2,.25,.22),3,.18)]:
        data=bpy.data.lights.new(light,'AREA');data.energy=power;data.size=size;o=bpy.data.objects.new(light,data);scene.collection.objects.link(o);o.location=loc;aim(o,(0,0,0))
    data=bpy.data.cameras.new('FoodIcon');cam=bpy.data.objects.new('FoodIcon',data);scene.collection.objects.link(cam);cam.location=(.055,-.22,.28);aim(cam,(0,0,0));data.type='ORTHO';scene.camera=cam
    bpy.context.view_layer.update();points=[cam.matrix_world.inverted()@(obj.matrix_world@v.co) for v in obj.data.vertices]
    lo=[min(p[i] for p in points) for i in range(2)];hi=[max(p[i] for p in points) for i in range(2)]
    cam.location+=cam.matrix_world.to_3x3()@Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0));data.ortho_scale=max(hi[i]-lo[i] for i in range(2))/.85
    icon=row['raw'] if state=='Raw' else row['cooked'];scene.render.filepath=str(OUT/'Icons'/f'{icon}.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Blends'/f'{name}.blend'));bpy.ops.render.render(write_still=True)
    records.append({'id':icon,'mesh':name,'dimensions_cm':[round(v*100,3) for v in obj.dimensions],'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),
        'source':'Existing project Medieval Banquet sausage mesh; locally reshaped exposed portion, original grip/bite ends retained',
        'maps':['BaseColor sRGB','Roughness linear','Tangent normal OpenGL'],'icon':'512x512 RGBA actual model','gameplay_test':False})
    (OUT/'model-authoring.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('CAMPFIRE_FOOD_MODELS_SAVED',len(records))
