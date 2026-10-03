"""Reuse the closed plate/true-seat authoring method of the previous guard."""
from pathlib import Path
P=Path(__file__).resolve().parent;S=P.parent/'XuanCloudGuard20261002'
s=(S/'author_guard.py').read_text(encoding='utf-8')
for old,new in [('xuan_cloud_dragon','phoenix_feather'),('XuanCloud','PhoenixFeather'),('XUAN_CLOUD','PHOENIX_FEATHER'),('璇云龙璧','凤仪华羽')]:s=s.replace(old,new)
s=s.replace("MAT='M_TangDaoPhoenixFeatherGuard'","MAT='M_TangDaoPhoenixFeatherGuard_Gilt';GEM_MAT='M_TangDaoPhoenixFeatherGuard_Garnet'")
s=s.replace('W=.144;H=.164','W=.134;H=.178;ART_OFFSET_X=.020')
s=s.replace('smooth=[]','smooth=[];material_indices=[]')
s=s.replace('def add(v,fs,uvs,sm=True):','def add(v,fs,uvs,sm=True,material=0):')
s=s.replace('smooth.append(sm)','smooth.append(sm);material_indices.append(material)' ,1)
s=s.replace('(-W/2+W*i/(nx-1),','(-W/2+ART_OFFSET_X+W*i/(nx-1),')
s=s.replace('def face(indices,uvs,sm=True):faces.append(indices);uvfaces.append(uvs);smooth.append(sm)',
            'def face(indices,uvs,sm=True):faces.append(indices);uvfaces.append(uvs);smooth.append(sm);material_indices.append(0)')
s=s.replace('(x/W+.5)','((x-ART_OFFSET_X)/W+.5)')
s=s.replace('carving=.00014*math.sin(8*a+1.8*math.sin((z+.05)/.064*10*math.pi))','carving=0.0 # Keep the manufactured collar straight; engraving is a fine normal map.')
s=s.replace('uv.extend([[(.797,.4)]*n,[(.797,.4)]*n]);add(v,fs,uv)',
'''# Planar UVs for both closed installation caps; constant UVs would create
    # zero-length tangents in the imported metal surfaces.
    xs=[p[0] for p in v];ys=[p[1] for p in v]
    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
    for cap in fs[-2:]:
        uv.append([(.783+.024*(v[i][0]-xmin)/max(xmax-xmin,1e-6),.24+.52*(v[i][1]-ymin)/max(ymax-ymin,1e-6)) for i in cap])
    add(v,fs,uv)''')
start=s.index("mat=bpy.data.materials.new(MAT)");end=s.index("obj=bpy.data.objects.new(NAME+'_LOD0'",start)
materials='''for family,name in [('Gilt',MAT),('Garnet',GEM_MAT)]:
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    for key in ['BaseColor','ORM','Normal']:
        im=bpy.data.images.load(str(P/'Textures'/('TangDao_PhoenixFeatherGuard_'+family+'_'+key+'.png')))
        im.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
        node=nt.nodes.new('ShaderNodeTexImage');node.image=im
        if key=='BaseColor':nt.links.new(node.outputs[0],bs.inputs['Base Color'])
        elif key=='ORM':
            sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(node.outputs[0],sep.inputs[0])
            nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
        else:
            nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(node.outputs[0],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
    mesh.materials.append(mat)
'''
s=s[:start]+materials+s[end:]
s=s.replace('poly.use_smooth=smooth[poly.index]','poly.use_smooth=smooth[poly.index];poly.material_index=material_indices[poly.index]')
gem_code='''# Closed cabochons on both sides, individually inset into their raised bezels.
gems=json.loads((P/'Ornament/gemstones.json').read_text(encoding='utf-8'))
for g in gems:
    for sign in [1,-1]:
        cx,cy=g['x_m'],g['y_m'];rx,ry=g['radius_x_m'],g['radius_y_m']
        z0=.0070 if sign==1 else -.0076;dome=g['dome_height_m'];segments=64;levels=10
        # Substantial gilded bezel/seat reaches the metal plate and supports
        # the inset stone; the cabochon is not suspended above the relief.
        bezel=[];bf=[];bu=[]
        profile=[(1.18,z0-sign*.0026),(1.22,z0-sign*.00045),(1.13,z0+sign*.00012),(1.01,z0+sign*.00012),(.99,z0-sign*.0006)]
        for r,z in profile:
            for i in range(segments):
                theta=2*math.pi*i/segments
                bezel.append((cx+rx*r*math.cos(theta),cy+ry*r*math.sin(theta),z))
        for j in range(len(profile)-1):
            for i in range(segments):bf.append([j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i])
        bf.extend([list(range(segments-1,-1,-1)),[(len(profile)-1)*segments+i for i in range(segments)]])
        for f in bf:bu.append([(.795+.010*(bezel[i][0]-cx)/rx,.5+.32*(bezel[i][1]-cy)/ry) for i in f])
        add(bezel,bf,bu,sm=True,material=0)
        v=[];uv=[];fs=[]
        for j in range(levels):
            a=(j/levels)*math.pi/2;r=math.cos(a);z=z0+sign*dome*math.sin(a)
            for i in range(segments):
                theta=2*math.pi*i/segments
                v.append((cx+rx*r*math.cos(theta),cy+ry*r*math.sin(theta),z))
        top=len(v);v.append((cx,cy,z0+sign*dome))
        bottom=len(v);v.append((cx,cy,z0-sign*.0008))
        for j in range(levels-1):
            for i in range(segments):fs.append([j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i])
        for i in range(segments):
            fs.append([(levels-1)*segments+i,(levels-1)*segments+(i+1)%segments,top])
            fs.append([(i+1)%segments,i,bottom])
        for f in fs:uv.append([(.5+.49*(v[i][0]-cx)/rx,.5+.49*(v[i][1]-cy)/ry) for i in f])
        add(v,fs,uv,sm=True,material=1)

'''
s=s.replace('mesh=bpy.data.meshes.new(NAME);',gem_code+'mesh=bpy.data.meshes.new(NAME);')
s=s.replace("'materials':{MAT:UE+'/Materials/'+MAT+'.'+MAT},","'materials':{name:UE+'/Materials/'+name+'.'+name for name in [MAT,GEM_MAT]},")
s=s.replace("'relief_height_mm':2.5","'relief_height_mm':3.1")
s=s.replace("'texture_resolution':4096","'texture_resolution':{'Gilt':4096,'Garnet':512},'art_offset_x_cm':2.0,'gemstones_per_side':len(gems)")
s=s.replace("['四瓣璇云层叠外廓','双面实体龙云浮雕','云纹贯通镂空及封闭内壁','鎏金凸纹与暗铜凹底','龙鳞蚀刻','承力芯与雕纹止滑环']",
"['非对称凤羽层叠外廓','双面凤首与羽脊实体浮雕','羽隙与卷云贯通镂空及实体孔壁','暖鎏金凸纹与暗铜凹底','双面红石独立嵌饰','精确承力芯与雕纹止滑环']")
s=s.replace('Closed double-sided scalloped dragon relief, pierced clouds, exact TangDao seats.','Closed double-sided phoenix feather relief and garnet insets, using exact TangDao seats.')
(P/'author_guard.py').write_text(s,encoding='utf-8')
icon=(S/'render_menu_icon.py').read_text(encoding='utf-8')
for old,new in [('xuan_cloud_dragon','phoenix_feather'),('XuanCloud','PhoenixFeather'),('XUAN_CLOUD','PHOENIX_FEATHER')]:icon=icon.replace(old,new)
icon=icon.replace('center=Vector((0,0,-.008))','center=Vector((.020,0,-.008))').replace('ortho_scale=.215','ortho_scale=.235')
icon=icon.replace('from mathutils import Vector','from mathutils import Vector,Matrix')
icon=icon.replace("cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()",
                  "direction=(center-cam.location).normalized();up=Vector((0,1,0));right=direction.cross(up).normalized();up=right.cross(direction).normalized();cam.rotation_euler=Matrix((right,up,-direction)).transposed().to_euler()")
# Garnet retains dielectric roughness/metalness and is only desaturated for UI.
icon=icon.replace('for slot in obj.material_slots:\n    nt=',"for slot in obj.material_slots:\n    if 'Garnet' in slot.material.name:continue\n    nt=")
(P/'render_menu_icon.py').write_text(icon,encoding='utf-8')
ps=(S/'import_background.ps1').read_text(encoding='utf-8').replace('xuan_cloud_dragon','phoenix_feather')
(P/'import_background.ps1').write_text(ps,encoding='utf-8')
print('PHOENIX_GUARD_AUTHOR_PREPARED',flush=True)
