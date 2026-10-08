from pathlib import Path
import builtins
import unreal as u
OUT=Path(__file__).resolve().parent
f=builtins.zhenmo_fixture
f['capture'].capture_scene()
u.RenderingLibrary.export_render_target(f['world'],f['rt'],str(OUT),'fixture-original.png')
print('FIXTURE particles_active='+str(f['fx'].is_active())+' triangles='+str(f['comp'].get_dynamic_mesh().get_triangle_count()))
