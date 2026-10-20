"""Minimal lossless FBX binary reader/writer (versions 7100-7700).

Unmodified properties are written back from their original bytes, so an
untouched file round-trips byte for byte; replaced arrays are re-encoded
(zlib when the original array was compressed).
"""
import struct, zlib
from array import array

MAGIC = b'Kaydara FBX Binary  \x00\x1a\x00'
FOOTER_MAGIC = b'\xf8\x5a\x8c\x6a\xde\xf5\xd9\x7e\xec\xe9\x0c\xe3\x75\x8f\x29\x0b'
ARRAY_CODES = {'f': 'f', 'd': 'd', 'l': 'q', 'i': 'i', 'b': 'b'}


class Prop:
    __slots__ = ('code', 'raw', 'value', 'encoding', 'dirty')

    def __init__(self, code, raw=None, value=None, encoding=0):
        self.code, self.raw, self.value, self.encoding, self.dirty = code, raw, value, encoding, raw is None

    def get(self):
        if self.value is None:
            self.value = decode_prop(self.code, self.raw)
        return self.value

    def set(self, value):
        self.value, self.dirty = value, True


class Node:
    __slots__ = ('name', 'props', 'children', 'nested')

    def __init__(self, name, props=None, children=None, nested=False):
        self.name, self.props, self.children, self.nested = name, props or [], children or [], nested

    def find(self, name):
        return next((c for c in self.children if c.name == name), None)

    def find_all(self, name):
        return [c for c in self.children if c.name == name]


def decode_prop(code, raw):
    if code == 'Y': return struct.unpack('<h', raw)[0]
    if code == 'C': return raw[0] != 0
    if code == 'I': return struct.unpack('<i', raw)[0]
    if code == 'F': return struct.unpack('<f', raw)[0]
    if code == 'D': return struct.unpack('<d', raw)[0]
    if code == 'L': return struct.unpack('<q', raw)[0]
    if code in ('S', 'R'): return bytes(raw[4:])
    if code in ARRAY_CODES:
        n, enc, clen = struct.unpack('<3I', raw[:12])
        data = raw[12:12 + clen]
        if enc == 1: data = zlib.decompress(data)
        a = array(ARRAY_CODES[code]); a.frombytes(data)
        if len(a) != n: raise ValueError('array length mismatch')
        return a
    raise ValueError('unknown property type ' + code)


def encode_prop(p):
    if not p.dirty: return p.code.encode() + p.raw
    v, c = p.value, p.code
    if c == 'Y': body = struct.pack('<h', v)
    elif c == 'C': body = bytes((1 if v else 0,))
    elif c == 'I': body = struct.pack('<i', v)
    elif c == 'F': body = struct.pack('<f', v)
    elif c == 'D': body = struct.pack('<d', v)
    elif c == 'L': body = struct.pack('<q', v)
    elif c in ('S', 'R'): body = struct.pack('<I', len(v)) + v
    elif c in ARRAY_CODES:
        a = v if isinstance(v, array) and v.typecode == ARRAY_CODES[c] else array(ARRAY_CODES[c], v)
        data = a.tobytes()
        if p.encoding == 1: data = zlib.compress(data, 1)
        body = struct.pack('<3I', len(a), p.encoding, len(data)) + data
    else: raise ValueError(c)
    return c.encode() + body


class FBX:
    def __init__(self, path):
        self.buf = open(path, 'rb').read()
        if not self.buf.startswith(MAGIC): raise ValueError('not a binary FBX')
        self.version = struct.unpack('<I', self.buf[23:27])[0]
        self.wide = self.version >= 7500
        self.head = 'QQQ' if self.wide else 'III'
        self.hsize = struct.calcsize('<' + self.head)
        pos = 27; self.roots = []
        while True:
            node, pos = self._read(pos)
            if node is None: break
            self.roots.append(node)
        self.tail_start = pos
        tail = self.buf[pos:]
        self.foot_id = tail[:16]
        # Footer padding differs between writers (Blender vs FBX SDK); keep the original rule.
        zeros = len(tail) - 16 - 4 - 120 - 16
        self.pad_rule = 'blender' if zeros == 4 + self._pad('blender', pos + 16) else 'sdk' if zeros == 4 + self._pad('sdk', pos + 16) else zeros

    @staticmethod
    def _pad(rule, id_end):
        if rule == 'blender':
            p = ((id_end + 4 + 15) & ~15) - (id_end + 4); return p or 16
        p = 16 - (id_end % 16); return p

    def _read(self, pos):
        end, nprops, plen = struct.unpack_from('<' + self.head, self.buf, pos); pos += self.hsize
        nlen = self.buf[pos]; pos += 1
        if end == 0: return None, pos
        name = self.buf[pos:pos + nlen].decode('ascii', 'replace'); pos += nlen
        pend = pos + plen; props = []
        while pos < pend:
            code = chr(self.buf[pos]); pos += 1
            if code in ('Y',): size = 2
            elif code == 'C': size = 1
            elif code in ('I', 'F'): size = 4
            elif code in ('D', 'L'): size = 8
            elif code in ('S', 'R'): size = 4 + struct.unpack_from('<I', self.buf, pos)[0]
            elif code in ARRAY_CODES:
                n, enc, clen = struct.unpack_from('<3I', self.buf, pos); size = 12 + clen
                props.append(Prop(code, self.buf[pos:pos + size], encoding=enc)); pos += size; continue
            else: raise ValueError('bad property %r' % code)
            props.append(Prop(code, self.buf[pos:pos + size])); pos += size
        node = Node(name, props)
        if pos < end:
            node.nested = True
            while True:
                child, pos = self._read(pos)
                if child is None: break
                node.children.append(child)
        if pos != end: raise ValueError('node %s end mismatch' % name)
        return node, pos

    def _write(self, node, out):
        start = len(out)
        out += b'\0' * self.hsize
        name = node.name.encode('ascii')
        out += bytes((len(name),)) + name
        pstart = len(out)
        for p in node.props: out += encode_prop(p)
        plen = len(out) - pstart
        if node.nested:
            for c in node.children: self._write(c, out)
            out += b'\0' * (self.hsize + 1)
        struct.pack_into('<' + self.head, out, start, len(out), len(node.props), plen)

    def save(self, path):
        out = bytearray(self.buf[:27])
        for n in self.roots: self._write(n, out)
        out += b'\0' * (self.hsize + 1)
        out += self.foot_id
        pad = self._pad(self.pad_rule, len(out)) if isinstance(self.pad_rule, str) else self.pad_rule - 4
        out += b'\0' * (4 + pad) + struct.pack('<I', self.version) + b'\0' * 120 + FOOTER_MAGIC
        open(path, 'wb').write(out)
        return bytes(out)


if __name__ == '__main__':
    import sys, json, hashlib, tempfile, os
    files = json.load(open(sys.argv[1])) if sys.argv[1].endswith('.json') else sys.argv[1:]
    for f in files:
        fbx = FBX(f)
        tmp = os.path.join(tempfile.gettempdir(), 'fbx_roundtrip.fbx')
        data = fbx.save(tmp)
        same = data == fbx.buf
        print('ROUNDTRIP', 'IDENTICAL' if same else 'DIFF(%d vs %d)' % (len(data), len(fbx.buf)), f)
