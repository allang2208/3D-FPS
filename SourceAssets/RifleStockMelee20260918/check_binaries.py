"""核对编辑器/游戏二进制里是否含本轮改动（解锁 + 步枪砸击）。

UE 的 TEXT() 字面量是 UTF-16LE，导出符号名是 ASCII，两种都查。
"""
import os

TARGETS = [
    r'D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor-FPSGAME.dll',
    r'D:\FPS3D\FPSGAME\Binaries\Win64\FPSGAME.exe',
]

WIDE = [
    '不限武器类型',            # 技能页/规则默认描述（取消武器类型锁）
    '步枪砸击',                # 步枪入口日志
    '步枪双手持枪以枪托',      # skills.json / 技能页描述
]
NARROW = [
    'TriggerRifleStockMelee',
    'GetRifleStockMeleeProbe',
    'RifleQuickCombatClips',
    'M4StockMelee20260918',
]

for path in TARGETS:
    if not os.path.exists(path):
        print('MISSING', path)
        continue
    with open(path, 'rb') as handle:
        blob = handle.read()
    stamp = __import__('datetime').datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
    print('==', os.path.basename(path), stamp, len(blob), 'bytes')
    for text in WIDE:
        print('   wide  %-12s %s' % (text[:6], text.encode('utf-16-le') in blob))
    for text in NARROW:
        print('   ascii %-28s %s' % (text, text.encode('ascii') in blob))
