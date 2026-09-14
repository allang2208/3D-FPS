# 715 independent left-hand closing recovery

用户授权：检查并优化合仓时左手同步甩动的问题。范围是最后装填脱离至恢复持握，覆盖全部 21 个逐发与 6 个速装变体。

当前源继承 `DanWesson715ReloadNatural20260914`。左手脱离后采用独立视模空间回收轨迹；逐发最后一发不再返回取弹点；已取下的速装器跟随左手回收。枪体、右手、机械、声音接触和动作时长沿用原版。

源文件及制作：

- `author_actions.py`、`animation.json`、`DanWesson715_LeftRecovery_Editable.blend`、`Animations/`：可编辑参数及 27 个 120 Hz FBX。
- `source-close.json`：旧版问题区间姿态；`closing-inspection.json`：27 个尾段的限定检查结果。
- `Inspection/`：同一相机的源模型前后关键帧和运动对比，不是 PIE。
- `import_assets.py` / `import.json`：新引擎目录 `LeftRecovery20260914/Animations` 的导入及资源路径记录。
- 说明：`Docs/Weapons/dan-wesson715-left-recovery-20260914.md`。

源动画制作及指定区间检查已完成。27 个尾段中右手／机械轨迹保持原值，左手结束握点不变；灰底源模型前后关键帧和两份运动对比已制作。

初版引擎导入已完成：`import.json` 记录首批 27 个动作路径；最终六个速装片段采用下述独立路径。命令行另有工程既有 GameFeatureData 配置错误，未修改该既有配置。

最终必要构建 `build-final.log` 为 `Result: Succeeded`，耗时 25.18 秒，FPSGAME、AutoFootstep、AutoFootstepEditor 使用一致后缀 `71409`，包含最终 LoaderStow 路径。此前 `71408` 的 `build-native.log` 仅作初版记录。重启已打开的 UE 编辑器后加载新动作路径。检查限于本次源动画合仓／回握区间；未做 PIE、游戏回归或音效复测，最终游戏手感由用户测试。

最终速装回收细修：源模型连续对比发现 2.76 秒隐藏速装器时它仍在画面中，已将下收轨迹延长至 0.38 秒，并把视觉收起点改为 2.91 秒。对应时刻前后的源模型画面中左手与速装器均已退到画面下方。最终 Blend、FBX、动作检查记录和对比 GIF 已重新生成。旧路径在 single_0_6 和 speed_0 保存时出现文件占用（Error 32），因此保留已完成且未再改动的逐发资源，六个最终速装动作导入独立 `LeftRecovery20260914/LoaderStow`；结果记录为 `import-loader-stow.log` 和 `import-speed-final.json`。

最终六个速装动作已全部保存，日志记录 `DW715_SPEED_RECOVERY_FINAL_COMPLETE` 和 `Python script executed successfully`。当前有效资源为 21 个逐发片段及 6 个 LoaderStow 速装片段，合计 27 个；导入进程因既有 GameFeatureData 配置错误返回 1，最终六段资源保存已完成。
