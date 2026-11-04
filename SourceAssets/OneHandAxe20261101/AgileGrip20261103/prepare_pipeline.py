"""Keep the established entrypoints on the user-selected hollow model revision."""
from pathlib import Path
P=Path(__file__).resolve().parent
entries={'author_agile_grip.py':'author_hollow.py','render_icon_input.py':'render_icon_input.py',
         'import_agile_grip.py':'import_hollow.py','register_agile_grip.py':'register_hollow.py','record_delivery.py':'record_delivery.py'}
for entry,target in entries.items():
    before=P/'HollowV2/Before'/entry
    if not before.exists() and (P/entry).exists():before.write_bytes((P/entry).read_bytes())
    (P/entry).write_text('"""Active hollow-grip production entrypoint; V1 source remains in Before."""\n'
        'from pathlib import Path\nimport runpy\n'
        f"runpy.run_path(str(Path(__file__).resolve().parent/'HollowV2'/'{target}'),run_name='__main__')\n",encoding='utf-8')
print('HOLLOW_GRIP_ENTRYPOINTS_READY')
