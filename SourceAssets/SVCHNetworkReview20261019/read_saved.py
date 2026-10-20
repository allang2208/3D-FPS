from pathlib import Path
import unreal as u,json,hashlib
O=Path(__file__).resolve().parent;P=Path(u.Paths.project_dir()).resolve()
mesh=u.load_asset('/Game/Weapons/SniperSuppressor20261019/SM_SniperHeavySuppressor')
def xyz(v):return [v.x,v.y,v.z]
s=mesh.find_socket('Muzzle')
data={'suppressor_mesh':mesh.get_path_name(),'muzzle_socket':xyz(s.relative_location) if s else None,
    'bounds_origin':xyz(mesh.get_bounds().origin),'bounds_extent':xyz(mesh.get_bounds().box_extent),'profiles':{}}
q=P/'SourceAssets/SVCHReplacement20261018/QuickMeleeWrist20261019'
receipt=json.loads((q/'install_receipt.json').read_text())
for family,row in receipt['assets'].items():
    asset=u.load_asset(row['path']);clip=next(c for c in asset.get_editor_property('clips') if c.get_editor_property('base').get_name().endswith('quick_melee'))
    data['profiles'][family]={'path':asset.get_path_name(),'duration':clip.get_editor_property('duration'),
        'right_tracks':{str(t.get_editor_property('bone')):len(t.get_editor_property('times')) for t in clip.get_editor_property('tracks') if str(t.get_editor_property('bone')).endswith('_r')},
        'sha256':hashlib.sha256((P/'Content'/(row['path'].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()}
(O/'saved-assets.json').write_text(json.dumps(data,indent=2))
print('SVCH_SAVED_ASSETS_READ',json.dumps(data),flush=True)
