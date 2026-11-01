"""Derive owned JiLei author scripts from the accepted original-solid C workflow."""
from pathlib import Path
P=Path(__file__).resolve().parent
src=P.parent/'SeatInlaidC6'
design=(src/'design.py').read_text(encoding='utf-8')
begin=design.index('STYLES=[');end=design.index('\ndef smooth',begin)
design=design[:begin]+"""STYLES=[dict(id='ji_lei_seat',name='疾雷锤座',bulk=.0018,width=.0020,depth=.00135,
 paths=[[(.034,.974),(.045,.963),(.041,.957),(.053,.944)],
        [(.046,.974),(.056,.963),(.049,.956),(.059,.941)],
        [(.055,.972),(.061,.963),(.056,.956),(.061,.949)]],
 lower=True,seams=False,appearance='原厂雷纹圆徽 · 三路嵌银引雷纹 · 低矮锻钢引雷尖')]
""" + design[end:]
(P/'design.py').write_text(design,encoding='utf-8')
geo=(src/'author_geometry.py').read_text(encoding='utf-8')
geo=geo.replace('ThorSeatC6','JiLeiSeatV1').replace('ThorSeats_InlaidC6.blend','JiLeiSeatV1_Editable.blend')
geo=geo.replace("str(P.parent/'SeatNorseConceptV5/C_InlaidThunder.png')","str(P/'Design.png')")
geo=geo.replace(" bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj",
""" # Low forged lightning peak is rooted into the existing top cap. Native
 # socket, neck and lateral mating faces remain untouched.
 center_vertices=[v for v in mesh.vertices if abs(v.co.x-CX)<.018 and abs(v.co.y)<.022]
 top=max(v.co.z for v in center_vertices)
 verts=[(CX-.006,-.007,top-.001),(CX+.006,-.007,top-.001),(CX+.006,.007,top-.001),(CX-.006,.007,top-.001),
        (CX,-.003,top+.009),(CX,.003,top+.009)]
 faces=[(0,3,2,1),(0,1,4),(3,5,2),(0,4,5,3),(1,2,5,4)]
 fm=bpy.data.meshes.new('IntegratedLightningPeak');fm.from_pydata(verts,[],faces);fm.update()
 fin=bpy.data.objects.new('IntegratedLightningPeak',fm);bpy.context.collection.objects.link(fin);fm.materials.append(mat)
 uvfin=fm.uv_layers.new(name=mesh.uv_layers[0].name)
 native_uv=mesh.uv_layers[0].data
 cap_loops=[l.index for l in mesh.loops if mesh.vertices[l.vertex_index].co.z>top-.002 and abs(mesh.vertices[l.vertex_index].co.x-CX)<.018]
 anchor=native_uv[cap_loops[0]].uv.copy() if cap_loops else native_uv[0].uv.copy()
 for loop in fm.loops:
  co=fm.vertices[loop.vertex_index].co
  uvfin.data[loop.index].uv=anchor+__import__('mathutils').Vector((co.x-CX,co.z-top))*.25
 bpy.ops.object.select_all(action='DESELECT');fin.select_set(True);bpy.context.view_layer.objects.active=fin
 bevel=fin.modifiers.new('Forged edge radius','BEVEL');bevel.width=.00045;bevel.segments=3
 bpy.ops.object.modifier_apply(modifier=bevel.name)
 obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
 mesh=obj.data;mesh.calc_loop_triangles()
 p=np.array([tuple(v.co) for v in mesh.vertices],np.float64)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj""")
# The added fin has no deformed-vertex correspondence to the original array.
geo=geo.replace("int(np.sum(np.abs(p[:,1]-positions[:,1])>1e-9))","int(np.sum(np.abs(deformation(positions,s))>1e-9))")
(P/'author_geometry.py').write_text(geo,encoding='utf-8')
for name in ['author_textures.py','finish_source.py','import_assets.py']:
 text=(src/name).read_text(encoding='utf-8').replace('ThorSeatC6','JiLeiSeatV1').replace('ThorSeats_InlaidC6.blend','JiLeiSeatV1_Editable.blend')
 text=text.replace('/SeatInlaidC6','/JiLeiSeatV1').replace("len(manifest['parts'])==5","len(manifest['parts'])==1")
 (P/name).write_text(text,encoding='utf-8')
print('JI_LEI_AUTHORS_READY',flush=True)
