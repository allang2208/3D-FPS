"""Export only the revised stair assembly, seven junction layers per theme and PPE body."""
import bpy,bmesh,math,json,sys,hashlib,random,importlib.util
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;PROJECT=PARENT.parents[1];OUT=ROOT/'Authored';BASE='/Game/Dungeons/FacilityTransit20261007/RefineV3'
ROLES=json.loads((ROOT/'materials.json').read_text('utf8'))
src=(PARENT/'author.py').read_text('utf8');ctx={'__file__':str(PARENT/'author.py'),'__name__':'stair_base_recipe'}
exec(compile(src[:src.index('records=[]')],'stair_base_recipe','exec'),ctx)
g=ctx['g'];stair_kinds={'Steps','Nosings','StairSupport','Landings','StairPiers','Rails','GalleryFascia'}
hall_g={k:v for k,v in g.G.items() if k[0]=='Hall' and k[1] in stair_kinds};hall_c={k:v for k,v in g.C.items() if k in hall_g}
g.G.clear();g.C.clear()
portal=(PARENT/'RefineV2/author.py').read_text('utf8');pc={'__file__':str(PARENT/'RefineV2/author.py'),'__name__':'junction_recipe'}
exec(compile(portal[:portal.index('# Use the established export path')],'junction_recipe','exec'),pc)
g=pc['g'];portal_kinds={'StructuralBody','Throat','PassagePanels','PassageKickplate','PassageReveals','LiningBacker','EntryReturns'}
for key in list(g.G):
    if key[1] not in portal_kinds:g.G.pop(key,None);g.C.pop(key,None)
g.G.update(hall_g);g.C.update(hall_c)
materials={}
for k,r in ROLES.items():
    m=bpy.data.materials.new('FT3_'+k);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*r['basecolor_linear'],1);p.inputs['Roughness'].default_value=r.get('roughness',.5);p.inputs['Metallic'].default_value=r.get('metallic',0);materials[k]=m
out=src[src.index('records=[]'):src.index('# Accepted native breakable glass recipe')]
out=out.replace("name='SM_FT_'","name='SM_FT3_'").replace("'FT_'+r","'FT3_'+r").replace('mod.width=.0025;mod.segments=2','mod.width=.0015;mod.segments=3')
out=out.replace("coords[j] if coords else", "coords[j] if role in ('Labels','TechLabels') and coords else (coords[j][0]/s,coords[j][1]/s) if coords else")
exec(compile(out,'facility_v3_export','exec'),globals())
architecture=list(records)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Stairs_and_PortalJunctions.blend'))

# Reuse the original cabinet shell, shelves and hinge coordinates. Replace its contents
# as one fixed mesh; retain the existing interactive door and all saved container IDs.
ppe_source=PROJECT/'SourceAssets/IncineratorContainers20261003/Scripts/author_containers.py';cs=ppe_source.read_text('utf8');c={'__file__':str(ppe_source),'__name__':'ppe_shell_source'}
exec(compile(cs[:cs.index('toolbox();ppe_locker()')],'ppe_shell_source','exec'),c)
c['OUT']=OUT
map_=dict(c['MAP'])
map_.update(Rubber=ROLES['Gasket']['existing_ue_path'],Steel=ROLES['Brushed']['existing_ue_path'],Gray=ROLES['Ivory']['existing_ue_path'],Charcoal=ROLES['Graphite']['existing_ue_path'],
            Fabric=ROLES['PPEFabric']['existing_ue_path'],Webbing=ROLES['Gasket']['existing_ue_path'],Seam=ROLES['PPEFabric']['existing_ue_path'],PPELabels=ROLES['PPELabels']['existing_ue_path'])
for k in ('Fabric','Webbing','Seam','PPELabels'):
    m=bpy.data.materials.new('RS_'+k);m.use_nodes=True;c['MATS'][k]=m
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.24,.22,.16,1) if k!='Webbing' else (.025,.031,.026,1);p.inputs['Roughness'].default_value=.82
def ppe_label(center,w,h,row,horizontal=False):
    x,y,z=center
    if horizontal:vs=[(x-w/2,y-h/2,z),(x+w/2,y-h/2,z),(x+w/2,y+h/2,z),(x-w/2,y+h/2,z)]
    else:vs=[(x-w/2,y,z-h/2),(x+w/2,y,z-h/2),(x+w/2,y,z+h/2),(x-w/2,y,z+h/2)]
    me=bpy.data.meshes.new('Native aspect PPE label');me.from_pydata(vs,[],[(0,1,2,3)] if horizontal else [(0,3,2,1)]);me.update();ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob);me.materials.append(c['MATS']['PPELabels']);uv=me.uv_layers.new(name='UVMap')
    v0=1-(row+1)*.5;v1=1-row*.5;coords=[(0,v0),(1,v0),(1,v1),(0,v1)]
    for li in me.polygons[0].loop_indices:uv.data[li].uv=coords[me.loops[li].vertex_index]
    c['parts'].append(ob)
c['ppe_label']=ppe_label
sp=importlib.util.spec_from_file_location('ppe_detail_recipe',ROOT/'ppe_recipe.py');ppe=importlib.util.module_from_spec(sp);sp.loader.exec_module(ppe)
c['detailed_contents']=lambda:ppe.contents(c)
code=cs[cs.index('def ppe_locker():'):cs.index('    # Real vent gaps:')]
a=code.index('    # Folded protection packs');b=code.index('    fixed_hinges(');code=code[:a]+'    detailed_contents()\n'+code[b:]
def emit_body(name,pivot=(0,0,0),hulls=()):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in c['parts']:ob.select_set(True)
    bpy.context.view_layer.objects.active=c['parts'][0];bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_FT3_PPELocker_Body';bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');ob.location=(0,0,0)
    # Fine twill repeats physically at 24 cm; label UVs remain authored and proportional.
    uv=ob.data.uv_layers['UVMap']
    for f in ob.data.polygons:
        if ob.data.materials[f.material_index].name in ('RS_Fabric','RS_Seam'):
            for li in f.loop_indices:uv.data[li].uv/= .24
    age=ob.data.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for a in age.data:a.color=(.025,0,0,1)
    col=[]
    for center,size in hulls:
        cx,cy,cz=center;sx,sy,sz=[s/2 for s in size];v=[(cx+x,cy+y,cz+z) for x,y,z in [(-sx,-sy,-sz),(sx,-sy,-sz),(sx,sy,-sz),(-sx,sy,-sz),(-sx,-sy,sz),(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz)]];col.append((v,g.FACES))
    # Existing body geometry has its intended bevels; do not bevel fine seams a second time.
    exp=out[out.index('def export('):out.index('for (room,kind),data in g.G.items():')].replace("'Glass','Fracture'):","'Glass','Fracture','PPEBody'):")
    exec(compile(exp,'ppe_export','exec'),globals())
    export(ob,'PPE','PPEBody',col,{m.name:map_[m.name.removeprefix('RS_')] for m in ob.data.materials},True)
c['emit']=emit_body
exec(compile(code,'refined_ppe_body','exec'),c);c['ppe_locker']()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'PPELocker_DetailedContents.blend'))
(ROOT/'manifest.json').write_text(json.dumps(dict(base=BASE,meshes=records,stair_kinds=sorted(stair_kinds),portal_kinds=sorted(portal_kinds),tests_run=False,rendered=False),indent=2),encoding='utf8')
print('FACILITY_V3_AUTHORED',len(records),flush=True)
