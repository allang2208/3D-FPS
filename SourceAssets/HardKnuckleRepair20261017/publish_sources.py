"""Publish repaired production JSONs after the native meshes have been saved."""
import hashlib,json,shutil
from pathlib import Path
O=Path(__file__).parent
OLD=O.parent/'BenelliM4Super9020261006'

def publish(require_saved=True):
    rows=json.loads((O/'author_receipt.json').read_text())
    receipt=json.loads((O/'import_receipt.json').read_text()) if require_saved else None
    for row in rows:
        src=Path(row['file']);sha=hashlib.sha256(src.read_bytes()).hexdigest()
        if require_saved and receipt['saved'][row['profile']]['sha256']!=sha:raise RuntimeError('Unsaved source '+row['profile'])
        dst=OLD/'EquipmentAuthored'/src.name
        # Preserve any later authoring edit instead of overwriting it silently.
        current=hashlib.sha256(dst.read_bytes()).hexdigest()
        if current not in (row['previous_source_sha256'],sha):raise RuntimeError('Source changed during this repair '+str(dst))
        shutil.copy2(src,dst)
        if require_saved:
            saved=OLD/'EquipmentSaved'/src.name
            if saved.exists() and not (O/'Before'/('saved_'+src.name)).exists():shutil.copy2(saved,O/'Before'/('saved_'+src.name))
            saved.write_text(json.dumps({'profile':row['profile'],'item':'ue_hardknuckle_gloves','mesh':row['asset'],'sha256':sha,'runtime_tested':False,'repair':'HardKnuckleRepair20261017'},indent=2))
    print('HARDKNUCKLE_PRODUCTION_SOURCES_PUBLISHED',len(rows))

if __name__=='__main__':publish()
