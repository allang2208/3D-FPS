from pathlib import Path
O=Path(__file__).parent
exec((O/'verify_assets.py').read_text(encoding='utf-8-sig'))
exec((O/'verify_mat_saved.py').read_text(encoding='utf-8-sig'))
