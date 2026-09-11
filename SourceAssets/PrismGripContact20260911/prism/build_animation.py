from pathlib import Path
# Contact configuration lives here; the vertical-grip family owns the generator.
source=Path(__file__).resolve().parents[2]/"VerticalGripClass20260911/build_family.py"
exec(compile(source.read_text(encoding="utf-8"),str(source),"exec"))
