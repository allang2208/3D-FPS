"""Export the saved generator's catalog without loading UE or editing its assets.

The production external actor package is authoritative. This reads its serialized
FString, not a historical source snapshot, and preserves replaced exports in the
requested receipt directory. It does not generate or test a dungeon.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import uuid


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_catalog(package: Path) -> tuple[dict, str]:
    data = package.read_bytes()
    marker = '{"version"'.encode('utf-16-le')
    offset = 0
    candidates = []
    while (offset := data.find(marker, offset)) >= 0:
        start = offset
        offset += len(marker)
        if start < 4:
            continue
        length = struct.unpack_from('<i', data, start - 4)[0]
        if length >= 0 or -length > 16_000_000:
            continue
        end = start + (-length * 2)
        if end > len(data) or data[end - 2:end] != b'\0\0':
            continue
        try:
            value = json.loads(data[start:end - 2].decode('utf-16-le'))
        except (UnicodeError, ValueError):
            continue
        if isinstance(value, dict) and 'modules' in value and 'themed_routes' in value:
            candidates.append(value)
    if len(candidates) != 1:
        raise RuntimeError(f'Expected one saved facility catalog, found {len(candidates)} in {package}')
    return candidates[0], digest(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor-package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bank-output', type=Path)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    package = args.actor_package.resolve(strict=True)
    catalog, source_hash = read_catalog(package)
    targets = [(args.output.resolve(), catalog)]
    if args.bank_output:
        targets.append((args.bank_output.resolve(), catalog['facility_flow']['layout_bank']))
    receipt = args.receipt.resolve()
    if receipt.exists():
        raise FileExistsError(receipt)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    run = uuid.uuid4().hex[:12]
    rows = []
    for target, value in targets:
        previous = target.read_bytes() if target.exists() else None
        payload = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f'.{target.name}.{run}.tmp')
        temporary.write_bytes(payload)
        # Both the source package and an existing export can change while another
        # authoring session saves. Abort instead of publishing a stale snapshot.
        if digest(package.read_bytes()) != source_hash:
            temporary.unlink()
            raise RuntimeError('Production package changed during export; rerun from its new saved state')
        if (target.read_bytes() if target.exists() else None) != previous:
            temporary.unlink()
            raise RuntimeError(f'Export changed concurrently: {target}')
        backup = None
        if previous is not None:
            backup = receipt.parent / f'{run}-before-{target.name}'
            shutil.copy2(target, backup)
        os.replace(temporary, target)
        rows.append({'path': str(target), 'sha256': digest(payload), 'previous': str(backup) if backup else None})
    result = {'source_package': str(package), 'source_sha256': source_hash,
              'bank_contract_sha1': catalog['facility_flow']['layout_bank']['contract_sha1'],
              'exports': rows, 'asset_modified': False, 'gameplay_tested': False}
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
