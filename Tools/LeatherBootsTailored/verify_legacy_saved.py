"""Fresh-process check of the historical packages repaired during the review."""
import sys,hashlib
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
receipt=read(R/'Audit/legacy_displays.json');rows=[]
for path,row in receipt['saved'].items():
    actual=u.load_asset(path);current=u.load_asset(row['source']);assert actual and current
    mats=lambda a:[s.material_interface.get_path_name() for s in a.static_materials]
    assert mats(actual)==mats(current)
    counts=[actual.get_num_triangles(i) for i in range(3)];expected=[current.get_num_triangles(i) for i in range(3)]
    assert counts==expected and counts[0]>0,(path,counts,expected)
    rows.append(dict(asset=path,source=current.get_path_name(),triangles=counts,materials=mats(actual)))
write(R/'Audit/legacy_saved_check.json',dict(completed=True,fresh_process=True,rows=rows,rendered=False))
print('BOOT_LEGACY_SAVED_CHECK_PASSED',len(rows),flush=True)
