"""Read the weapon-root motion of a fire animation straight from its FBX source.

The runtime fire animation is a separate authored asset per weapon while the
procedural springs are shared, so a per-weapon recoil difference can live in the
clip. This reader prints the peak travel (cm) and peak turn (degrees) per axis of
one bone over the whole clip, taken from the authoring values.

Arrays are kept as raw slices and only decoded on demand: several of these FBX
files carry large geometry buffers, and decoding them all is both slow and
memory hungry.

Usage: python Tools/AssetPipeline/read_animation_curves_fbx.py <file.fbx> [bone]
"""
import array
import math
import struct
import sys
import zlib

MAX_ARRAY = 8_000_000
STRIDE = {'f': 4, 'd': 8, 'l': 8, 'i': 4, 'b': 1}


class Node:
    __slots__ = ('name', 'props', 'children', 'end')

    def __init__(self, name, props, end):
        self.name = name
        self.props = props
        self.children = []
        self.end = end


def decode_array(code, raw, length):
    stride = STRIDE[code]
    if len(raw) < length * stride:
        raise ValueError('array shorter than declared')
    return array.array({'f': 'f', 'd': 'd', 'l': 'q', 'i': 'i', 'b': 'b'}[code],
                       raw[:length * stride]).tolist()


def read_props(buf, pos, count, limit):
    props = []
    for _ in range(count):
        if pos >= limit:
            raise ValueError('property list runs past the record end')
        code = buf[pos:pos + 1]
        pos += 1
        if code == b'Y':
            props.append(struct.unpack_from('<h', buf, pos)[0]); pos += 2
        elif code == b'C':
            props.append(buf[pos]); pos += 1
        elif code == b'I':
            props.append(struct.unpack_from('<i', buf, pos)[0]); pos += 4
        elif code == b'F':
            props.append(struct.unpack_from('<f', buf, pos)[0]); pos += 4
        elif code == b'D':
            props.append(struct.unpack_from('<d', buf, pos)[0]); pos += 8
        elif code == b'L':
            props.append(struct.unpack_from('<q', buf, pos)[0]); pos += 8
        elif code in b'fdlib':
            length, encoding, comp_len = struct.unpack_from('<III', buf, pos)
            pos += 12
            if pos + comp_len > limit or length > MAX_ARRAY:
                raise ValueError('implausible array length %d' % length)
            raw = buf[pos:pos + comp_len]
            pos += comp_len
            if encoding == 1:
                raw = zlib.decompress(raw)
            props.append(('array', code.decode(), length, raw))
        elif code == b'S':
            length = struct.unpack_from('<I', buf, pos)[0]; pos += 4
            if pos + length > limit:
                raise ValueError('implausible string length')
            raw = buf[pos:pos + length]; pos += length
            props.append(raw.rstrip(b'\0').decode('utf-8', 'replace'))
        elif code == b'R':
            length = struct.unpack_from('<I', buf, pos)[0]; pos += 4
            if pos + length > limit:
                raise ValueError('implausible raw length')
            props.append(buf[pos:pos + length]); pos += length
        else:
            raise ValueError('unknown property code %r at %d' % (code, pos))
    return props, pos


def parse_node(buf, pos, wide):
    head = 8 if wide else 4
    end = struct.unpack_from('<Q' if wide else '<I', buf, pos)[0]
    if end == 0:
        return None, pos + head * 3
    nprop = struct.unpack_from('<Q' if wide else '<I', buf, pos + head)[0]
    plen = struct.unpack_from('<Q' if wide else '<I', buf, pos + 2 * head)[0]
    nlen = buf[pos + 3 * head]
    if end > len(buf) or nprop > 100000:
        raise ValueError('implausible record at %d (end=%d nprop=%d)' % (pos, end, nprop))
    name = buf[pos + 3 * head + 1:pos + 3 * head + 1 + nlen].decode('utf-8', 'replace')
    node = Node(name, None, end)
    node.props, child_pos = read_props(buf, pos + 3 * head + 1 + nlen, nprop, end)
    while child_pos < end:
        child, child_pos = parse_node(buf, child_pos, wide)
        if child is None:
            break
        node.children.append(child)
    if child_pos > end:
        raise ValueError('record at %d overruns its end' % pos)
    return node, end


def roots_of(buf):
    version = struct.unpack_from('<I', buf, 23)[0]
    wide = version >= 7500
    roots = []
    pos = 27
    while pos < len(buf):
        node, pos = parse_node(buf, pos, wide)
        if node is None:
            break
        roots.append(node)
    return version, roots


def find(node, name):
    for child in node.children:
        if child.name == name:
            return child
    return None


def objects_of(roots, kind):
    """Map object id -> node for every object of one FBX kind."""
    out = {}
    for root in roots:
        if root.name != 'Objects':
            continue
        for obj in root.children:
            if obj.name == kind and obj.props:
                label = obj.props[1] if len(obj.props) > 1 else ''
                if isinstance(label, str) and '\0' in label:
                    label = label.split('\0')[0]
                out[obj.props[0]] = (obj, label)
    return out


def links_of(roots):
    """All (child, parent) object links. Curve nodes attach to bones with OP."""
    out = []
    for root in roots:
        if root.name != 'Connections':
            continue
        for conn in root.children:
            if conn.name == 'C' and conn.props and conn.props[0] in ('OO', 'OP'):
                out.append((conn.props[1], conn.props[2]))
    return out


def axis_map(curve_node):
    """curve id -> axis index, from the node's d|X / d|Y / d|Z properties."""
    out = {}
    props = find(curve_node, 'Properties70')
    if not props:
        return out
    for entry in props.children:
        if entry.name != 'P' or len(entry.props) < 5:
            continue
        name = entry.props[0]
        if name in ('d|X', 'd|Y', 'd|Z') and isinstance(entry.props[4], int):
            out[entry.props[4]] = 'XYZ'.index(name[-1])
    return out


def curve_axes(curve):
    """Return (times in seconds, values) for one AnimationCurve, or None."""
    times = find(curve, 'KeyTime')
    values = find(curve, 'KeyValueFloat')
    if not times or not values:
        return None
    _, code, length, raw = times.props[0]
    t = [x / 46186158000.0 for x in decode_array(code, raw, length)]
    _, code, length, raw = values.props[0]
    v = decode_array(code, raw, length)
    return t, v


def op_links(roots):
    """(child, parent, channel) for every OP connection; axis and bone live here."""
    out = []
    for root in roots:
        if root.name != 'Connections':
            continue
        for conn in root.children:
            if conn.name == 'C' and conn.props and conn.props[0] == 'OP' and len(conn.props) > 3:
                out.append((conn.props[1], conn.props[2], conn.props[3]))
    return out


def main(path, bone):
    with open(path, 'rb') as handle:
        buf = handle.read()
    version, roots = roots_of(buf)
    models = objects_of(roots, 'Model')
    curves = objects_of(roots, 'AnimationCurve')
    curve_nodes = objects_of(roots, 'AnimationCurveNode')
    ops = op_links(roots)
    targets = [oid for oid, (_, label) in models.items() if label == bone]
    print('%s version=%d models=%d curves=%d' % (path, version, len(models), len(curves)))
    if not targets:
        print('  bones:', sorted({label for _, label in models.values()})[:30])
        return
    target = targets[0]
    axes_of = {}
    for child, parent, name in ops:
        if name in ('d|X', 'd|Y', 'd|Z') and child in curves:
            axes_of[child] = 'XYZ'.index(name[-1])
    for node_id, _, channel in [op for op in ops if op[1] == target and op[0] in curve_nodes]:
        axes = {}
        for curve_id, parent, _ in ops:
            if parent != node_id or curve_id not in curves:
                continue
            axis = axes_of.get(curve_id)
            pair = curve_axes(curves[curve_id][0])
            if pair is not None and axis is not None:
                axes[axis] = pair
        if not axes:
            continue
        rotate = 'otation' in channel
        report = []
        for axis in sorted(axes):
            times, values = axes[axis]
            base = values[0]
            peak, when = 0.0, 0.0
            for time, value in zip(times, values):
                delta = abs(value - base)
                if delta > peak:
                    peak, when = delta, time
            # Blender FBX carries metres; the rigs are metric through the import.
            report.append((axis, peak if rotate else peak * 100.0, when))
        print('  %-16s %s' % (channel, '  '.join(
            '%s=%.3f%s@%.3fs' % ('XYZ'[axis], peak, 'deg' if rotate else 'cm', when)
            for axis, peak, when in report)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'WPN_root')
