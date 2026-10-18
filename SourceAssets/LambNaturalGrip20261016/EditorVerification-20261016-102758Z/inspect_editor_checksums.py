"""Read CodeView source checksums from existing Editor objects; no project writes."""
from pathlib import Path
import struct, hashlib, json, datetime

ROOT = Path('D:/FPS3D/FPSGAME')
OBJ = ROOT / 'Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME'
NAMES = ('FPSPotionUseComponent.cpp', 'PotionArmPose.cpp', 'PotionUseMotion.cpp')

def checksums(path):
    blob = path.read_bytes()
    big = blob[:4] == b'\x00\x00\xff\xff'
    count = struct.unpack_from('<I' if big else '<H', blob, 44 if big else 2)[0]
    section_table = 56 if big else 20 + struct.unpack_from('<H', blob, 16)[0]
    subsections = []
    for i in range(count):
        offset = section_table + i * 40
        if blob[offset:offset + 8] != b'.debug$S':
            continue
        size, pointer = struct.unpack_from('<II', blob, offset + 16)
        data = blob[pointer:pointer + size]
        if data[:4] != b'\x04\x00\x00\x00':
            continue
        cursor = 4
        while cursor + 8 <= len(data):
            kind, length = struct.unpack_from('<II', data, cursor)
            assert cursor + 8 + length <= len(data)
            subsections.append((kind, data[cursor+8:cursor+8+length]))
            cursor = (cursor + 8 + length + 3) & ~3
    strings = [value for kind, value in subsections if kind == 0xF3]
    assert len(strings) == 1, (path.name, len(strings))
    string_table = strings[0]
    result = []
    for kind, data in subsections:
        if kind != 0xF4:
            continue
        cursor = 0
        while cursor + 6 <= len(data):
            name_index, length, algorithm = struct.unpack_from('<IBB', data, cursor)
            end = string_table.index(b'\x00', name_index)
            name = string_table[name_index:end].decode('utf-8')
            digest = data[cursor+6:cursor+6+length].hex()
            if '/source/fpsgame/items/' in name.replace('\\', '/').lower() and Path(name).name.lower() in [x.lower() for x in (*NAMES, 'PotionUseMotion.h')]:
                method = {1: 'md5', 2: 'sha1', 3: 'sha256'}[algorithm]
                actual = hashlib.new(method, Path(name).read_bytes()).hexdigest()
                result.append({'source': name, 'algorithm': method, 'compiled_checksum': digest, 'current_checksum': actual, 'matches': digest == actual})
            cursor = (cursor + 6 + length + 3) & ~3
    return result

if __name__ == '__main__':
    result = {name: checksums(OBJ / (name + '.obj')) for name in NAMES}
    print(json.dumps(result, indent=2))
