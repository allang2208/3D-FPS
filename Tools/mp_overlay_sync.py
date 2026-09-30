import filecmp, os, shutil, sys

SRC = r'D:/FPS3D/FPSGAME'
DST = r'D:/FPS3D/FPSGAME-mp'
TOPS = ['Source', 'Config']

copied = removed = 0
for top in TOPS:
    # 1) 主仓 -> worktree：新增/内容不同的一律覆盖
    for root, dirs, files in os.walk(os.path.join(SRC, top)):
        rel = os.path.relpath(root, SRC)
        dstdir = os.path.join(DST, rel)
        os.makedirs(dstdir, exist_ok=True)
        for f in files:
            s = os.path.join(root, f)
            d = os.path.join(dstdir, f)
            if not os.path.exists(d):
                shutil.copy2(s, d); copied += 1
            elif os.path.getsize(s) != os.path.getsize(d) or not filecmp.cmp(s, d, shallow=False):
                shutil.copy2(s, d); copied += 1
    # 2) worktree 独有（主仓已删/改名旧文件）-> 移除，避免陈旧符号
    for root, dirs, files in os.walk(os.path.join(DST, top)):
        rel = os.path.relpath(root, DST)
        srcdir = os.path.join(SRC, rel)
        for f in files:
            d = os.path.join(root, f)
            if not os.path.exists(os.path.join(srcdir, f)):
                os.remove(d); removed += 1
        for dd in list(dirs):
            if not os.path.exists(os.path.join(srcdir, dd)):
                shutil.rmtree(os.path.join(root, dd), ignore_errors=True)

print(f'overlay sync done: copied={copied} removed={removed}')
