import math, time, unreal
SV = unreal.ModelingService
D = '/Game/Props/RomanColumn20260915'; V = 20.0
COL = D + '/SM_RomanColumn_Detailed'; SEG = D + '/SM_BalustradeSegment_20'; STONE = D + '/M_RomanStone_V2'
DETAIL = D + '/T_Stone_V2_Detail'
def tf(x=0,y=0,z=0):
    t=unreal.Transform(); t.translation=unreal.Vector(x,y,z); t.rotation=unreal.Rotator(0,0,0).quaternion(); t.scale3d=unreal.Vector(1,1,1); return t
def do(l,r): print('[ed] %-12s %s' % (l, getattr(r,'success',None)))
col = SV.create_mesh().handle
SV.append_box(col, tf(0,0,0), 4*V,4*V,V,0,0,0,'Base',0)
SV.append_cylinder(col, tf(0,0,V), 1.9*V, 0.6*V, 64,0,True,'Base',0)
SV.append_torus(col, tf(0,0,1.6*V), 1.6*V, 0.4*V, 48,12,'Base',0)
SV.append_cone(col, tf(0,0,2.4*V), 1.6*V, 1.15*V, 0.6*V, 64,2,True,'Base',0)
SV.append_cylinder(col, tf(0,0,3*V), 1.15*V, 8*V, 64,8,True,'Base',0)
SV.append_torus(col, tf(0,0,10.9*V), 1.05*V, 0.25*V, 48,10,'Base',0)
SV.append_cone(col, tf(0,0,11*V), 1.15*V, 1.8*V, V, 64,3,True,'Base',0)
SV.append_box(col, tf(0,0,12*V), 4*V,4*V,V,0,0,0,'Base',0)
tool = SV.create_mesh().handle
for i in range(20):
    a=2*math.pi*i/20
    SV.append_cylinder(tool, tf(math.cos(a)*1.15*V, math.sin(a)*1.15*V, 3*V), 2.2, 8*V, 24,0,True,'Base',0)
SV.boolean(col, tool, 'Subtract', tf(), True, True); SV.release_mesh(tool)
try:
    SV.compute_polygroups(col,'Angle',24.0,2); do('bevel', SV.bevel_polygroups(col,0.15,1,1.0))
except Exception as e: print('[ed] bevel skip', e)
do('uv', SV.auto_uv(col,'XAtlas',0))
do('displace', SV.displace_from_texture(col,'',DETAIL+'.'+DETAIL.split('/')[-1],0.10,0))
i = SV.get_mesh_info(col)
print('[ed] column h=%.0f base=%.0f tris=%s comps=%s open=%s' % (i.bounds_max.z-i.bounds_min.z, i.bounds_max.x-i.bounds_min.x, i.triangle_count, i.connected_components, i.open_border_edges))
do('save', SV.save_mesh_to_static_mesh(col, COL, True, True, False, True)); SV.release_mesh(col)
end=time.time()+20
while time.time()<end:
    if unreal.EditorAssetLibrary.load_asset(COL): break
    time.sleep(0.3)
do('collision', SV.generate_collision(COL,'ConvexHulls',10,25,True))
do('material', SV.set_asset_materials(COL, STONE, True))
a = unreal.EditorAssetLibrary.load_asset(COL)
m = a.get_editor_property('static_materials')[0].get_editor_property('material_interface')
print('[ed] verify column slot0 =', m.get_path_name().split('.')[-1])
