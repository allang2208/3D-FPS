"""Author the approved full third-person ice armour on the native Jason rig.
Background geometry production only; no render or runtime test.
"""
import json, math
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/IceArmor20261017/ThirdPersonV6'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
body=read('SourceAssets/JasonPlayer20261003/Jason.json')
positions=[Vector(p) for p in body['positions']]
triangles=body['triangles']
bones={b['name']:Vector(b['position']) for b in body['bones']}
bone_ids={b['name']:i for i,b in enumerate(body['bones'])}

def tree(data):return BVHTree.FromPolygons([Vector(p) for p in data['positions']],data['triangles'],all_triangles=True)
skin=tree(body)
head=tree(read('SourceAssets/JasonPlayer20261003/head_geometry.json'))
cloth=tree(read('SourceAssets/JasonEquipmentRepair20261003/sweater.json'))
mail=tree(read('SourceAssets/JasonEquipmentRepair20261003/chainmail.json'))
steel_data=read('SourceAssets/JasonPlayer20261003/ue_steel_gauntlets_fitted.json')
steel_data['triangles']=read('SourceAssets/JasonPlayer20261003/ue_steel_gauntlets.json')['triangles']
steel=tree(steel_data)
glove_data=read('SourceAssets/JasonPlayer20261003/ue_field_gloves_fitted.json')
glove_data['triangles']=read('SourceAssets/JasonPlayer20261003/ue_field_gloves.json')['triangles']
glove=tree(glove_data)
cloth_pants=[tree(read('SourceAssets/LowerBodyEquipment20261003/'+n+'_fitted.json')) for n in ('jeans','cargo')]
cloth_pants.append(tree(read('SourceAssets/BrownLeatherSet20261004/Jason_LeatherPants.json')))
mail_pants=tree(read('SourceAssets/ChainmailPants20261004/ArmorRefineV2/Jason_ChainmailPants.json'))
cloth_boots=[tree(read('SourceAssets/BootsEquipment20261004/boots_fitted.json')),tree(read('SourceAssets/BrownLeatherSet20261004/Jason_LeatherBoots.json'))]
steel_boots=tree(read('SourceAssets/ArmoredBoots20261004/Jason_ArmoredBoots.json'))
pack_data=read('SourceAssets/BackpackHarnessRebuild20261020/Authored/bare.json')
backpack=tree(pack_data)

def weights(p,allowed=None):
    q,_,face,_=skin.find_nearest(p)
    ids=triangles[face];a,b,c=[positions[i] for i in ids]
    v0=b-a;v1=c-a;v2=q-a;den=v0.dot(v0)*v1.dot(v1)-v0.dot(v1)**2
    if abs(den)<1e-9:coeff=[1,0,0]
    else:
        v=(v1.dot(v1)*v2.dot(v0)-v0.dot(v1)*v2.dot(v1))/den
        w=(v0.dot(v0)*v2.dot(v1)-v0.dot(v1)*v2.dot(v0))/den
        coeff=[max(0,1-v-w),max(0,v),max(0,w)]
    accum={}
    for index,f in zip(ids,coeff):
        for bi,bw in body['weights'][index]:
            if allowed is None or body['bones'][bi]['name'] in allowed:accum[bi]=accum.get(bi,0)+f*bw
    if not accum:accum={bone_ids[min(allowed,key=lambda n:(bones[n]-p).length)]:1}
    pairs=sorted(accum.items(),key=lambda r:-r[1])[:8];total=sum(w for _,w in pairs)
    return [[i,w/total] for i,w in pairs]

def project(origin,direction,extras=(),radius=45,base=skin,allowed=None,rigid=None):
    direction=direction.normalized();start=origin+direction*radius
    p,_,_,distance=base.ray_cast(start,-direction,radius*2)
    if p is None:raise RuntimeError('Surface mapping missed: '+str(tuple(origin))+' '+str(tuple(direction)))
    surface=p
    for extra in extras:
        ep,_,_,ed=extra.ray_cast(start,-direction,radius*2)
        if ep is not None and ed<distance and (ep-p).length<14:surface=ep;distance=ed
    return surface,direction,[[bone_ids[rigid],1.]] if rigid else weights(p,allowed)

def blank(name):return {'name':name,'positions':[],'normals':[],'uv':[],'uv1':[],'uv2':[],'colors':[],'triangles':[],'weights':[],'skinned':True,'parts':[]}

def pack_mask(p,n):
    if p.z<80 or p.z>147:return 0.
    skin_point,_,_,_=skin.find_nearest(p)
    if n.dot(p-skin_point)<0:n=-n
    _,_,_,d=backpack.find_nearest(p)
    hit,_,_,ray=backpack.ray_cast(p+n*.1,n,20)
    return max(max(0.,min(1.,(5.5-d)/2.5)),1. if hit is not None else 0.)

def vertex(data,p,n,binding,uv,rim,thickness,zone):
    i=len(data['positions']);data['positions'].append(list(p));data['normals'].append(list(n))
    data['weights'].append(binding);data['uv'].append(uv)
    # Growth begins at chest, then spreads into head/arms/legs. The mask is
    # baked from the fitted backpack, including its shoulder straps.
    phase=min(.78,abs(p.z-129)/170+abs(p.x)/180)
    data['uv1'].append([pack_mask(p,n),phase]);data['uv2'].append([p.z/180,zone])
    data['colors'].append([rim,zone,thickness,1]);return i

def triangle(data,a,b,c,outward):
    p,q,r=[Vector(data['positions'][i]) for i in (a,b,c)]
    if (q-p).cross(r-p).dot(outward)<0:b,c=c,b
    # Native UE front winding is opposite Blender's outward RH cross product.
    data['triangles'].append([a,c,b])

def rounded(points,steps=3):
    result=[];count=len(points)
    for i in range(count):
        a,b,c,d=[Vector(points[j%count]) for j in (i-1,i,i+1,i+2)]
        for k in range(steps):
            t=k/steps
            result.append((2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)*.5)
    return result

def panel(data,label,outline,mapper,stand=1.1,thick=2.5,zone=0,steps=3):
    contour=rounded(outline,steps);count=len(contour);start=len(data['triangles'])
    centre=sum(contour,Vector((0,0)))/count
    mx=(mapper(centre.x+.1,centre.y)[0]-mapper(centre.x-.1,centre.y)[0]).length/.2
    my=(mapper(centre.x,centre.y+.1)[0]-mapper(centre.x,centre.y-.1)[0]).length/.2
    seed=sum(ord(c) for c in label)*.071
    def texture(t):return [t.x*mx/38+seed,t.y*my/38+seed*.37]
    # Wide bevel, dense enough curved core, and a genuine inner return surface.
    rings=[];out_normals=[]
    for scale,height,rim in [(1,0,.58),(1,.25,.92),(.96,.80,.70),(.87,1,.20),(.65,1.025,.06),(.34,1.04,.02)]:
        row=[];ns=[]
        for q in contour:
            t=centre+(q-centre)*scale;p,n,w=mapper(t.x,t.y)
            p=p+n*(stand+height*thick)
            row.append(vertex(data,p,n,w,texture(t),rim,.35+height*.65,zone));ns.append(n)
        rings.append(row);out_normals.append(ns)
    for k in range(len(rings)-1):
        for i in range(count):
            j=(i+1)%count;n=out_normals[k][i]+out_normals[k][j]
            triangle(data,rings[k][i],rings[k][j],rings[k+1][j],n)
            triangle(data,rings[k][i],rings[k+1][j],rings[k+1][i],n)
    p,n,w=mapper(centre.x,centre.y)
    mid=vertex(data,p+n*(stand+thick*1.05),n,w,texture(centre),.02,1.,zone)
    for i in range(count):triangle(data,rings[-1][i],rings[-1][(i+1)%count],mid,out_normals[-1][i])
    previous=rings[0]
    for scale in (.72,.38):
        row=[]
        for q in contour:
            t=centre+(q-centre)*scale;p,n,w=mapper(t.x,t.y)
            row.append(vertex(data,p+n*stand,-n,w,texture(t),.08,.5,zone))
        for i in range(count):
            j=(i+1)%count;n=-out_normals[0][i]-out_normals[0][j]
            triangle(data,previous[i],row[j],previous[j],n);triangle(data,previous[i],row[i],row[j],n)
        previous=row
    p,n,w=mapper(centre.x,centre.y)
    mid=vertex(data,p+n*stand,-n,w,texture(centre),.05,.4,zone)
    for i in range(count):triangle(data,previous[i],mid,previous[(i+1)%count],-out_normals[0][i])
    data['parts'].append({'name':label,'first_triangle':start,'triangles':len(data['triangles'])-start,'clearance_cm':stand,'thickness_cm':thick})

spine={f'spine_0{i}' for i in range(1,6)}|{'pelvis'}
def torso(extras,front=True):
    # Wrap the drawing around the actual torso section; a flat X/Z projection
    # extends outside the waist and cannot describe the side curvature.
    return lambda x,z:project(Vector((0,0,z)),Vector((x/12,1 if front else -1,0)),extras,allowed=spine)

def limb(side,begin,end,mid,span,angle,arc,extras,rigid=None):
    a=bones[begin+'_'+side];b=bones[end+'_'+side];axis=(b-a).normalized()
    forward=Vector((0,1,0));forward=(forward-axis*axis.dot(forward)).normalized();cross=axis.cross(forward).normalized()
    def mapper(x,y):
        t=mid+y*span;theta=angle+x*arc;rad=forward*math.cos(theta)+cross*math.sin(theta)
        return project(a.lerp(b,t),rad,extras,20,rigid=rigid)
    return mapper

limb_outline=[(-.66,-1),(.66,-1),(1,-.66),(.94,.67),(.56,1),(-.56,1),(-.94,.67),(-1,-.66)]
foot_slices={}
def foot_surface(side,x,y,extras):
    # End before the separate toe geometry; the ankle and toe joints stay open.
    z=3+(y+1)*3.2;key=(side,round(z,3))
    if key not in foot_slices:
        sign=1 if side=='l' else -1
        section=[p.x for p in positions if p.x*sign>4 and p.z<14 and abs(p.y-z)<.65]
        foot_slices[key]=((min(section)+max(section))*.5,(max(section)-min(section))*.5)
    mid,radius=foot_slices[key]
    return project(Vector((mid+x*radius*.64,z,0)),Vector((0,0,1)),extras,30,rigid='foot_'+side)
assets=[]
for shirt in range(3):
    extras=() if shirt==0 else (cloth,) if shirt==1 else (cloth,mail)
    d=blank(f'SK_IceArmorV6_Torso_{shirt}')
    panel(d,'Breastplate',[(0,139.2),(7,140.7),(12.2,138.2),(16.4,133.5),(15.2,121),(9,115),(0,113.8),(-9,115),(-15.2,121),(-16.4,133.5),(-12.2,138.2),(-7,140.7)],torso(extras),1.25,2.9)
    panel(d,'Backplate',[(-7,142),(7,142),(14,137),(15,125),(11,114),(0,113),(-11,114),(-15,125),(-14,137)],torso(extras,False),1.3,2.6,.25)
    for j,(z,width) in enumerate(((109.2,11),(101.9,10.5),(94.8,9.8))):
        outline=[(-width,z+3.3),(-width*.45,z+4),(width*.45,z+4),(width,z+3.3),(width*.96,z-2),(width*.45,z-3.4),(0,z-4),(-width*.45,z-3.4),(-width*.96,z-2)]
        panel(d,f'Abdominal_{j}',outline,torso(extras),1.3,1.8)
    for j,z in enumerate((106,98)):
        panel(d,f'Lumbar_{j}',[(-9,z+3),(9,z+3),(10,z-2),(0,z-3.5),(-10,z-2)],torso(extras,False),1.3,1.7,.25)
    assets.append(d)

for shirt in range(3):
    for gloves in range(3):
        sleeve=() if shirt==0 else (cloth,) if shirt==1 else (cloth,mail)
        fore=sleeve+(() if gloves==0 else (glove,) if gloves==1 else (steel,))
        d=blank(f'SK_IceArmorV6_Arms_{shirt}_{gloves}')
        for side,sign in (('l',1),('r',-1)):
            panel(d,'Pauldron_'+side,limb_outline,limb(side,'upperarm','lowerarm',.105,.17,sign*.95,1.15,sleeve),1.35,3.0,.5)
            panel(d,'UpperArm_'+side,limb_outline,limb(side,'upperarm','lowerarm',.50,.21,sign*.45,1.4,sleeve),1.15,2.0,.5)
            panel(d,'Forearm_'+side,limb_outline,limb(side,'lowerarm','hand',.53,.33,0,1.7,fore),1.2,2.3,.5)
        assets.append(d)

for pants in range(3):
    for boots in range(3):
        trousers=() if pants==0 else tuple(cloth_pants) if pants==1 else (mail_pants,)
        shoes=() if boots==0 else tuple(cloth_boots) if boots==1 else (steel_boots,)
        lower=trousers+shoes
        d=blank(f'SK_IceArmorV6_Legs_{pants}_{boots}')
        for side,sign in (('l',1),('r',-1)):
            panel(d,'Hip_'+side,limb_outline,limb(side,'thigh','calf',.09,.075,sign*1.25,.60,trousers),1.25,1.7,.75)
            panel(d,'ThighFront_'+side,limb_outline,limb(side,'thigh','calf',.49,.28,0,1.22,trousers),1.35,2.4,.75)
            panel(d,'ThighBack_'+side,limb_outline,limb(side,'thigh','calf',.48,.27,math.pi,.82,trousers),1.3,1.8,.75)
            knee=bones['calf_'+side]
            def kneemap(x,z,knee=knee):return project(Vector((knee.x,knee.y,knee.z+z*4.5)),Vector((x*.8,1,0)),trousers,20)
            panel(d,'Kneecap_'+side,limb_outline,kneemap,1.5,2.5,1.)
            panel(d,'Shin_'+side,limb_outline,limb(side,'calf','foot',.49,.34,0,1.55,lower),1.25,2.4,1.)
            panel(d,'CalfReturn_'+side,limb_outline,limb(side,'calf','foot',.48,.30,math.pi,.88,lower),1.25,1.6,1.)
            def footmap(x,y,side=side):return foot_surface(side,x,y,shoes)
            panel(d,'Instep_'+side,limb_outline,footmap,1.0,1.6,1.)
        assets.append(d)

helmet=blank('SK_IceArmorV6_Helmet')
centre=Vector((0,0,163));segments=64;rows=13
def dome(theta,f):
    # The front brow stops above the eyes. Sides/back extend down over the skull.
    blend=max(0.,min(1.,(abs(theta)-.55)/.85));blend=blend*blend*(3-2*blend)
    phi=(1.31+blend*.90)*f
    radial=Vector((math.sin(theta)*math.sin(phi),math.cos(theta)*math.sin(phi),math.cos(phi)))
    return project(centre,radial,(),45,head,rigid='head')
layers=[]
for outer in (True,False):
    grid=[]
    for j in range(1,rows+1):
        row=[];f=j/rows
        for i in range(segments):
            theta=-math.pi+2*math.pi*i/segments;p,n,w=dome(theta,f)
            clearance=2.0+max(0.,1-f)*.9
            edge=max(0.,(f-.84)/.16)
            thickness=1.8*(1-.25*edge)
            offset=clearance+(thickness if outer else 0)
            row.append(vertex(helmet,p+n*offset,n if outer else -n,w,[(theta+math.pi)/math.pi,f],.10+edge*.72,1 if outer else .45,.4))
        grid.append(row)
    p,n,w=dome(0,0);top=vertex(helmet,p+n*(2.9+(1.8 if outer else 0)),n if outer else -n,w,[.5,0],.10,1.,.4)
    for i in range(segments):
        k=(i+1)%segments
        triangle(helmet,top,grid[0][i],grid[0][k],Vector(helmet['normals'][grid[0][i]]))
    for j in range(rows-1):
        for i in range(segments):
            k=(i+1)%segments;n=Vector(helmet['normals'][grid[j][i]])
            triangle(helmet,grid[j][i],grid[j+1][i],grid[j+1][k],n);triangle(helmet,grid[j][i],grid[j+1][k],grid[j][k],n)
    layers.append(grid)
for i in range(segments):
    k=(i+1)%segments;a=layers[0][-1][i];b=layers[0][-1][k];c=layers[1][-1][k];e=layers[1][-1][i]
    theta=-math.pi+2*math.pi*(i+.5)/segments
    _,n,_=dome(theta,1);out=Vector((n.x,n.y,-.9)).normalized()
    triangle(helmet,a,c,b,out);triangle(helmet,a,e,c,out)
helmet['parts'].append({'name':'OpenFaceHelmetCap','triangles':len(helmet['triangles']),'clearance_cm':2,'thickness_cm':1.8})
for sign in (-1,1):
    def cheek(x,z,sign=sign):
        theta=sign*(.81+x*.34);rad=Vector((math.sin(theta),math.cos(theta),0))
        return project(Vector((0,0,157.2+z*5.8)),rad,(),35,head,rigid='head')
    panel(helmet,'Cheek_'+str(sign),[(-.48,-1),(.8,-.82),(1,.55),(.45,1),(-.55,.62),(-.8,-.2)],cheek,1.5,1.8,.4)
panel(helmet,'ChinGuard',[(-5.1,151.7),(0,150.7),(5.1,151.7),(5.6,149),(0,148.2),(-5.6,149)],lambda x,z:project(Vector((x,0,z)),Vector((0,1,0)),(),35,head,rigid='head'),1.65,1.7,.4)
assets.append(helmet)

# A saved Blender mesh remains editable with the original Jason vertex groups.
# Production normal accumulation uses the outward Blender winding, then stores
# the UE winding in JSON, retaining the earlier native front-face correction.
manifest=[]
for data in assets:
    normals=[Vector((0,0,0)) for _ in data['positions']]
    for a,c,b in data['triangles']:
        p,q,r=[Vector(data['positions'][i]) for i in (a,b,c)];n=(q-p).cross(r-p)
        for i in (a,b,c):normals[i]+=n
    data['normals']=[list(n.normalized()) if n.length>1e-8 else data['normals'][i] for i,n in enumerate(normals)]
    data['skeleton_source']=body['source'];data['rig_bones']=[b['name'] for b in body['bones']];data['triangle_winding']='unreal_clockwise'
    (OUT/(data['name']+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    mesh=bpy.data.meshes.new(data['name']);mesh.from_pydata(data['positions'],[],[(a,b,c) for a,c,b in data['triangles']]);mesh.update()
    for polygon in mesh.polygons:polygon.use_smooth=True
    for channel,key in [('IceSurface','uv'),('FitAndGrowth','uv1'),('HeightAndRegion','uv2')]:
        uv=mesh.uv_layers.new(name=channel)
        for loop in mesh.loops:uv.data[loop.index].uv=data[key][loop.vertex_index]
    color=mesh.color_attributes.new(name='IceAttributes',type='FLOAT_COLOR',domain='POINT')
    for i,c in enumerate(data['colors']):color.data[i].color=c
    ob=bpy.data.objects.new(data['name'],mesh);bpy.context.collection.objects.link(ob)
    for bone in data['rig_bones']:ob.vertex_groups.new(name=bone)
    for vi,binding in enumerate(data['weights']):
        for bi,w in binding:ob.vertex_groups[bi].add([vi],w,'REPLACE')
    ob.hide_set(not (data['name'].endswith('_1') or data['name'].endswith('_1_1') or data['name'].endswith('Helmet')))
    manifest.append({'name':data['name'],'vertices':len(data['positions']),'triangles':len(data['triangles']),'parts':data['parts']})
arm_data=bpy.data.armatures.new('Jason_ArmourV6_Bind');arm=bpy.data.objects.new('Jason_ArmourV6_Bind',arm_data);bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for source in body['bones']:
    bone=arm_data.edit_bones.new(source['name']);bone.head=Vector(source['position']);bone.tail=bone.head+Vector(source['axes'][0]).normalized()*1.5;bone.align_roll(Vector(source['axes'][2]))
    if source['parent']>=0:bone.parent=arm_data.edit_bones[body['bones'][source['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT')
for ob in bpy.context.scene.objects:
    if ob.type=='MESH':ob.modifiers.new('JasonPose','ARMATURE').object=arm
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'IceArmorThirdPersonV6.blend'))
(OUT/'geometry-manifest.json').write_text(json.dumps({'reference':'../ThirdPersonDesignV6/ice-armour-third-person-v2.png','assets':manifest,'skeleton':body['source'],'profiles':{'torso':'shirt 0 bare / 1 cloth / 2 metal','arms':'shirt x gloves, each 0..2','legs':'pants x boots, each 0..2'},'rendered':False},indent=2),encoding='utf-8')
print('ICE_ARMOR_V6_GEOMETRY_AUTHORED '+str(len(assets)),flush=True)
