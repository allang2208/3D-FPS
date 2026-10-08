"""Replace the owned mode-9 branch, retaining every other rune and PBR expression."""
def replace_jingang_branch(code,source):
    marker='// Jingang mode 9:'
    start=code.find(marker)
    if start<0:return source.rstrip()+'\n'+code
    opening=code.find('{',start)
    if opening<0:raise RuntimeError('Jingang branch has no opening brace')
    depth=0
    for end in range(opening,len(code)):
        if code[end]=='{':depth+=1
        elif code[end]=='}':
            depth-=1
            if depth==0:return code[:start]+source.rstrip()+code[end+1:]
    raise RuntimeError('Jingang branch has no closing brace')
