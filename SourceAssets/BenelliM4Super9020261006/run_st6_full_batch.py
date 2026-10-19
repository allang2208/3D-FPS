"""Combined ST6/glove batch: shirt SK rebuilds + owner mesh + pickup, then the
hardknuckle glove pickup re-import. Runs inside UE via -run=pythonscript."""
from pathlib import Path

O = Path(__file__).parent
for name in ("run_st6_shirt_batch.py", "run_glove_pickup_batch.py"):
    src = (O / name).read_text(encoding="utf-8")
    exec(compile(src, str(O / name), "exec"), {"__file__": str(O / name)})
print("ST6_FULL_BATCH_DONE", flush=True)
