"""Blender solid wall signs: one printed front face, bevels, spacers and fasteners."""
import json,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
sys.path.insert(0,str(HALL/'SceneFix20260930/Scripts'))
import author_fixes as fx
from author_fixes import equipment as eq,g
CFG=json.loads((ROOT/'Config/layout.json').read_text(encoding='utf-8'))
ATLAS=json.loads((ROOT/'Authored/sign_atlas.json').read_text(encoding='utf-8'))

def tex(surface,u,v):
    x0,y0,x1,y1=ATLAS['rects'].get(surface,ATLAS['rects']['steel'])
    return ((x0+u*(x1-x0))/2048,1-(y0+v*(y1-y0))/2048)

def board(identifier,c,w,h,surface,axis):
    eq.part(identifier);c=Vector(c);n,u,v=g.basis(axis)
    # Face is 12 mm from masonry: 5 mm folded plate + 7 mm mounting spacers.
    fx.solid_nameplate(c,w,h,surface,axis,.005)
    for a in (-1,1):
        for b in (-1,1):
            point=c+u*a*(w*.5-.035)+v*b*(h*.5-.030)
            g.lathe(point-n*.012,n,[(0,.007),(.007,.007)],'steel',16)
            g.bolt(point+n*.0002,n,.55)

def signs():
    for i,x in enumerate(CFG['furnace_centres_x']):
        board('Furnace_%02d_number_board'%(i+1),(x,CFG['furnace_sign_face_y'],3.83),1.95,.359,'furnace'+str(i+1),(0,1,0))
        board('Furnace_%02d_out_of_service'%(i+1),(x,CFG['furnace_sign_face_y'],3.39),.98,.281,'stop',(0,1,0))
    for spec in CFG['signs']:board(spec['id'],spec['centre_m'],*spec['size_m'],spec['surface'],spec['normal'])

bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
g.tex=tex;g.MATERIAL=CFG['ue_base']+'/Materials/M_IncineratorSigns'
mat=bpy.data.materials.new('IncineratorSigns');mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.67
image=bpy.data.images.load(str(ROOT/'Authored/Textures/T_IncineratorSigns_BaseColor.png'));image.pack()
sample=mat.node_tree.nodes.new('ShaderNodeTexImage');sample.image=image
mat.node_tree.links.new(sample.outputs['Color'],bsdf.inputs['Base Color'])
fx.ROOT=ROOT;fx.BASE=CFG['ue_base'];record=fx.export('HallSigns',signs,[],mat,'_V1');record['collision_policy']='none'
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/IncineratorHall_SignageV1.blend'))
(ROOT/'Authored/manifest.json').write_text(json.dumps({'revision':CFG['revision'],'objects':[record],
    'board_count':8,'tests_run':False,'rendered':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('INCINERATOR_SOLID_SIGNS_AUTHORED',8,flush=True)
