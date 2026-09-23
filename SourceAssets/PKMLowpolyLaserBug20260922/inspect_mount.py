"""Measure the laser mount for each family: root axes, emitter offset and beam angle.

The laser aims along the tactical body's Emitter -> AimGuide sockets in the weapon's
own frame, and on ADS it re-aims from that emitter toward the shot direction. This
rebuilds Configure()'s attachment off-level and reports, per family:
  * the weapon mesh's WPN_root axes, so the authored mesh convention is known;
  * where the Emitter ends up relative to the weapon root;
  * the beam axis in weapon space;
  * whether that axis is parallel to the barrel (front sight - rear sight).
Nothing is spawned into the level and nothing is saved.
"""
import unreal as u

CASES = [
    ('M4',  '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
            '/Game/Weapons/TacticalDevices20260913/M4/laser/SM_TacticalDevice'),
    ('AKM', '/Game/Weapons/AKM/SK_AKM_Viewmodel',
            '/Game/Weapons/TacticalDevices20260913/AKM/laser/SM_TacticalDevice'),
    ('PKM', '/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular',
            '/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_laser'),
]

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
lines = []
for family, vm_path, dev_path in CASES:
    vm = u.load_asset(vm_path)
    dev = u.load_asset(dev_path)
    if vm is None or dev is None:
        lines.append('%-5s missing asset (vm=%s dev=%s)' % (family, vm is not None, dev is not None))
        continue
    vmc = u.new_object(u.SkeletalMeshComponent, world)
    vmc.set_skinned_asset_and_update(vm)
    vmc.set_world_transform(u.Transform(), False, False)

    def socket(name):
        ok = vmc.does_socket_exist(name)
        if not ok:
            return None, None
        return vmc.get_socket_location(name), vmc.get_socket_rotation(name)

    root_loc, root_rot = socket('WPN_root')
    lines.append('%-5s WPN_root loc=%s' % (family, root_loc))
    if root_rot:
        f = root_rot.get_forward_vector()
        r = root_rot.get_right_vector()
        up = root_rot.get_up_vector()
        lines.append('      root fwd=(%5.2f,%5.2f,%5.2f) right=(%5.2f,%5.2f,%5.2f) up=(%5.2f,%5.2f,%5.2f)'
                     % (f.x, f.y, f.z, r.x, r.y, r.z, up.x, up.y, up.z))

    fs, _ = socket('WPN_FrontSight')
    rs, _ = socket('WPN_RearSight')
    if fs and rs:
        barrel = (fs - rs)
        n = max(barrel.length(), 1e-9)
        lines.append('      front-rear=(%5.2f,%5.2f,%5.2f) len=%.1f' % (barrel.x, barrel.y, barrel.z, n))

    body = u.new_object(u.StaticMeshComponent, world)
    body.set_static_mesh(dev)
    body.set_relative_transform(
        u.Transform(location=u.Vector(0.0, 0.0, 0.0), rotation=u.Rotator(0.0, 0.0, 0.0),
                    scale=u.Vector(0.01, 0.01, 0.01)), False, False)
    attached = body.attach_to_component(vmc, 'WPN_root', u.AttachmentRule.KEEP_RELATIVE,
                                        u.AttachmentRule.KEEP_RELATIVE, u.AttachmentRule.KEEP_RELATIVE,
                                        False)
    if not attached:
        lines.append('      attach failed')
        continue
    a = body.get_socket_location('Emitter')
    b = body.get_socket_location('AimGuide')
    d = b - a
    n = max(d.length(), 1e-9)
    lines.append('      attached Emitter=(%8.3f,%8.3f,%8.3f) AimGuide=(%8.3f,%8.3f,%8.3f)'
                 % (a.x, a.y, a.z, b.x, b.y, b.z))
    lines.append('      beam axis=(%6.3f,%6.3f,%6.3f) len=%.3f   offset from root=(%.3f,%.3f,%.3f)'
                 % (d.x / n, d.y / n, d.z / n, n, a.x - root_loc.x, a.y - root_loc.y, a.z - root_loc.z))

text = '\n'.join(lines)
u.log('PKM_LASER_MOUNT\n' + text)
print(text)
