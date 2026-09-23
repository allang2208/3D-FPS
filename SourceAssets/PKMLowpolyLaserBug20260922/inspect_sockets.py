"""Read the Emitter / AimGuide sockets through the component API.

StaticMesh.sockets is protected for direct Python reads, but a StaticMeshComponent
exposes GetSocketLocation/Rotation. A temporary component is created, measured and
then destroyed, so nothing is added to the level or saved.
"""
import unreal as u

FAMILIES = {
    'M4': '/Game/Weapons/TacticalDevices20260913/M4/laser/SM_TacticalDevice',
    'AKM': '/Game/Weapons/TacticalDevices20260913/AKM/laser/SM_TacticalDevice',
    'QBZ191': '/Game/Weapons/TacticalDevices20260913/QBZ191/laser/SM_TacticalDevice',
    'PKM': '/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_laser',
    'A762': '/Game/Weapons/A762/Accessories05/Meshes/SM_A762_laser',
    'M16': '/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_laser',
    'ASH12': '/Game/Weapons/ASH12/TacticalDevices20260920/laser/SM_ASH12_laser',
}

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
lines = []
for family, path in FAMILIES.items():
    mesh = u.load_asset(path)
    if mesh is None:
        lines.append('%-8s MISSING' % family)
        continue
    try:
        names = [str(n) for n in mesh.get_socket_names()]
    except Exception:
        names = []
    if 'Emitter' not in ' '.join(names) and not any('Emitter' in n for n in names):
        # Fall back to the asset-level query below; report what we can see.
        lines.append('%-8s socket names: %s' % (family, names if names else '(none readable)'))
    comp = u.new_object(u.StaticMeshComponent, world)
    comp.set_static_mesh(mesh)
    try:
        has = (comp.does_socket_exist('Emitter'), comp.does_socket_exist('AimGuide'))
        if not all(has):
            lines.append('%-8s Emitter=%s AimGuide=%s  -> component early-returns (no laser)'
                         % (family, has[0], has[1]))
            continue
        a = comp.get_socket_location('Emitter')
        b = comp.get_socket_location('AimGuide')
        d = b - a
        size = max(d.length(), 1e-9)
        lines.append('%-8s Emitter=(%8.2f,%8.2f,%8.2f) AimGuide=(%8.2f,%8.2f,%8.2f)'
                     % (family, a.x, a.y, a.z, b.x, b.y, b.z))
        lines.append('         axis=(%6.3f,%6.3f,%6.3f)  |axis|=%.2f cm' % (d.x / size, d.y / size, d.z / size, size))
    finally:
        pass

text = '\n'.join(lines)
u.log('PKM_LASER_SOCKETS\n' + text)
print(text)
