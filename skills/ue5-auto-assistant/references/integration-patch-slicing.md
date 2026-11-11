# 并行脏工作区里生成 HEAD 相对 Integration 补丁

适用：多会话共用一份工作区，目标文件里同时叠着自己和别人的未发布改动，只能按功能切片发布共享宿主。

## 为什么不能整文件提交

共享宿主（`ColdSteelPlayerState`、`FPSGAMECharacter`、`FPSPlayerBody*`、`KukriWeaponComponent` 等）会被多个会话同时修改。整文件 `git add` 会把别人尚未验收的层（新组件、网络回执、外观模块）一起推上公开 main。规则：**共享宿主只发布 HEAD 相对补丁**，武器自有宿主/生成头/作者源/文档可以直接提交。

## 用 hunk 筛选，不用手写 diff

手写 `difflib` 很容易踩换行差异（CRLF vs LF）导致整文件看起来都改了。可靠做法：

1. `git diff -U3 HEAD -- <host>` 拿到完整 unified diff；
2. 按 `@@` 切 hunk；
3. 每个 hunk 的正文里搜本任务的**唯一标记**（新增的函数名、字段名、常量名、注释里独有的词）；
4. 命中的 hunk 原样拼回（含原 header），未命中的丢弃。

```python
header, hunks, cur = [], [], None
for ln in diff.splitlines(keepends=True):
    if ln.startswith("@@"):
        if cur: hunks.append("".join(cur))
        cur = [ln]
    elif cur is None: header.append(ln)
    else: cur.append(ln)
if cur: hunks.append("".join(cur))
kept = [h for h in hunks if any(m in h for m in markers)]
```

标记要选**新增行里独有的字符串**。只出现在上下文里的词会误捕邻接 hunk（`-U3` 的上下文可以带进别人的改动）。生成后必须回读每个补丁，确认没有把别人的 `+` 行带进来。

## 验证

- `git archive HEAD <path> | tar -x -C /tmp/verify` 造一份干净 HEAD 导出；
- 逐个 `git apply --check`；
- 应用后再和真实工作区 diff，剩余差异**应当全部是别人未发布的层**；如果剩余里有本任务的内容，说明标记漏了。
- `git diff --check` 会把补丁里以单空格开头的上下文行报成"trailing whitespace"。这是补丁格式本身的，不是源码问题；应用时用 `git apply --whitespace=nowarn`。

## 无法做成 HEAD 相对补丁的情形

目标文件在 HEAD 上是**旧版本**（还没有别人稍后重构出的结构），本任务的改动是叠在那层上面的：补丁不可能应用到旧 HEAD 上。处理方式：

- 随本批提交**工作区整文件**；
- 在 `integration-prerequisites.json` 的 `whole_file` 里写明依赖和当前散列；
- README 里明确"等那一层发布后自然带上"。

## 提交时不碰共享索引

共享 `.git/index` 里可能有别的会话的暂存内容（甚至整目录 `D` 状态）。用临时索引：

```bash
export GIT_INDEX_FILE=/tmp/task_index
git read-tree HEAD
git add -- <本任务路径...>     # 只用精确路径，绝不 git add -A
tree=$(git write-tree)
commit=$(git commit-tree $tree -p $(git rev-parse HEAD) -F msg.txt)
git update-ref refs/heads/main $commit $(git rev-parse HEAD)   # CAS，HEAD 被抢时失败
```

提交后**只对本批路径**把共享索引同步到新 HEAD（`git update-index --add --cacheinfo 100644,<blob>,<path>`），不要碰其它会话的暂存项。工作区里因别人暂存删除而出现的 `D ` + `??` 组合，只修复"工作区内容 == HEAD"的那部分。

## 推送

普通非强制 `git push origin HEAD:main`，随后 `git ls-remote origin refs/heads/main` 回读 SHA 与关键文件路径。
