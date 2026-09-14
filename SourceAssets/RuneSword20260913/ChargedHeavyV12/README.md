# ChargedHeavyV12

LeftPrimaryV14 更新后，左键点按普通攻击，长按固定 2 秒蓄满、松开重击；不足 2 秒松开接普通攻击，右键暂不绑定动作。基础攻速下重击快速段 75 ms，释放整段 1 秒，重击武器伤害倍率 2。

完整说明：`D:/FPS3D/FPSGAME/Docs/Weapons/RuneSwordChargedHeavy20260914.md`。

- `author_heavy.py` / `heavy_motion.py`：制作新重击全链路姿态，导出 480 Hz 动画与更宽的空间扰动带。
- `action_timebase.py`：保留普通动作在新可编辑文件中的原有秒数。
- `AzureRunesword_Manny_Editable.blend` / `Export/`：可编辑源与 FBX。
- `import_revision.py` / `run_import.ps1`：新动画和重击扰动导入现有 UE 剑目录。
- `build_install.ps1`：必要原生构建及同批次模块快照。
- `authoring.json`、`import_receipt.json`、`build.log`：制作、导入、构建记录。

已完成导出、导入、Editor 构建。按用户规则未运行游戏测试、动画检查或渲染。
