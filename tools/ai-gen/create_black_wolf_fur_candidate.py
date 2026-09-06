"""Create the independent black-wolf material build from the proven canine bake tools."""
from pathlib import Path
import shutil
BASE=Path(__file__).resolve().parent
old=BASE/'zombie-dog-v01-20260906'
new=BASE/'black-wolf-fur-v01-20260906'
new.mkdir(exist_ok=True)
shutil.copy2(old/'fur-source.png',new/'fur-source.png')
src=(old/'build_zombie_dog.py').read_text(encoding='utf-8')
start=src[:src.index('WOUNDS=[')]
start=start.replace('Author a textured, skinned zombie canine','Author a black fur wolf')
start=start.replace("bpy.ops.wm.open_mainfile(filepath=str(R/'source-wolf.blend'))", "bpy.ops.wm.read_factory_settings(use_empty=True)\nbpy.context.scene.render.fps=30\nbpy.ops.import_scene.gltf(filepath=str(R.parents[2]/'assets/models/wolf_quaternius.gltf'))")
start=start.replace('# Add one local interpolation level for shallow wounds without a new skeleton.\nbmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True)\n','')
uv=src[src.index('# Non-overlapping UV atlas'):src.index('procedurals=[];bake_channels=[]')]
uv=uv.replace("wound_image=bpy.data.images.load(str(R/'wound-source.png'));wound_image.pack()\n",'')
materials='''procedurals=[];bake_channels=[]
for material_index,oldmat in enumerate(list(body.data.materials)):
    mat=bpy.data.materials.new('BlackWolf_'+['Coat','Nose','Undercoat','Eyes'][material_index]+'_Editable')
    mat.use_nodes=True;mat.use_fake_user=True;nt=mat.node_tree;nt.nodes.clear()
    output=node(nt,'ShaderNodeOutputMaterial','Surface')
    bs=node(nt,'ShaderNodeBsdfPrincipled','Editable PBR');nt.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
    bs.inputs['Metallic'].default_value=0
    coord=node(nt,'ShaderNodeTexCoord','Rest-space anatomy');position=coord.outputs['Object']
    if material_index in [0,2]:
        mapping=node(nt,'ShaderNodeMapping','Fur direction and strand scale')
        mapping.inputs['Rotation'].default_value=(math.pi/2,0,0)
        mapping.inputs['Scale'].default_value=(1.15,1.15,1.15)
        nt.links.new(position,mapping.inputs['Vector'])
        fur=node(nt,'ShaderNodeTexImage','Existing generated canine fur source')
        fur.image=fur_image;fur.projection='BOX';fur.projection_blend=.25;fur.extension='REPEAT'
        nt.links.new(mapping.outputs['Vector'],fur.inputs['Vector'])
        bw=node(nt,'ShaderNodeRGBToBW','Fur strand height');nt.links.new(fur.outputs['Color'],bw.inputs[0])
        color=ramp(nt,bw.outputs[0],[(.0,(.004,.005,.006)),(.14,(.028,.030,.034)),(.50,(.09,.093,.10)),(1.,(.14,.15,.16))],'Black coat with charcoal highlights')
        if material_index==2:
            color=mix(nt,.12,color,(.09,.09,.085),'Subtle charcoal undercoat')
        rough=ramp(nt,bw.outputs[0],[(0.,.86),(.6,.69)],'Natural dry fur roughness')
        bump=node(nt,'ShaderNodeBump','Short fur micro relief')
        bump.inputs['Strength'].default_value=.55;bump.inputs['Distance'].default_value=.030
        nt.links.new(bw.outputs[0],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    elif material_index==1:
        fine=noise(nt,position,90,2,'Nose pores')
        color=ramp(nt,fine,[(.0,(.004,.004,.004)),(1.,(.016,.017,.018))],'Black nose')
        rough=ramp(nt,fine,[(0.,.26),(1.,.38)],'Nose moisture')
        bump=node(nt,'ShaderNodeBump','Nose micro relief');bump.inputs['Distance'].default_value=.004
        nt.links.new(fine,bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    else:
        eye=node(nt,'ShaderNodeRGB','Healthy amber eyes');eye.outputs[0].default_value=(.30,.115,.015,1)
        color=eye.outputs[0]
        rough=mathnode(nt,'ADD',.22,0)
    nt.links.new(color,bs.inputs['Base Color']);nt.links.new(rough,bs.inputs['Roughness'])
    body.data.materials[material_index]=mat
    procedurals.append(mat);bake_channels.append((color,rough,bs,output))

'''
tail=src[src.index("textures=R/'textures'"):]
tail=tail.replace('ZombieDog','BlackWolf').replace('ZOMBIE_DOG','BLACK_WOLF').replace('zombie-dog-v01','black-wolf-fur-v01')
tail=tail.replace('Baked fur and wound normals','Baked short fur normals')
tail=tail.replace("'max_sculpt_source_units':max_sculpt", "'max_sculpt_source_units':0")
tail=tail.replace("'wounds':WOUNDS,", "'wounds':[],")
tail=tail.replace("'wound_method':'localized texture projection and shallow mesh recess on original interpolated skin'", "'geometry_method':'weld matching split vertices, preserve source triangles and positions, smooth normals; no sculpt or subdivision'")
(new/'build_black_wolf.py').write_text(start+uv+materials+tail,encoding='utf-8')
for name in ['check_asset.py','render_review.gd','prepare_review.py','package_preview.py']:
    text=(old/name).read_text(encoding='utf-8')
    text=text.replace('zombie-dog-v01-20260906','black-wolf-fur-v01-20260906').replace('zombie-dog-preview-20260906','black-wolf-fur-preview-20260906')
    text=text.replace('zombie-dog-v01','black-wolf-fur-v01').replace('ZombieDog','BlackWolf').replace('ZOMBIE_DOG','BLACK_WOLF')
    text=text.replace('zombie-dog-review','black-wolf-review').replace('僵尸犬 · 现有骨架与动作','黑色皮毛优化 · 原骨架与动作')
    text=text.replace('Zombie dog material review','Black wolf fur material review').replace('zombie','wolf').replace('wound-detail','fur-detail')
    (new/name).write_text(text,encoding='utf-8')
print('BLACK_WOLF_CANDIDATE_SCRIPTS_READY',new)
