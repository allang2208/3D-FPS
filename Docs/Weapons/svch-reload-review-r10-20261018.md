# SVCH 普通／空仓换弹复查与修复 R10

2026-10-18，按用户要求检查左手抓匣、手腕形变与穿模，并在保持认可源动画和 V9 手模的前提下继续修复。当前 R10 配置已保存，后台构建及两种换弹的实际运行复查已完成。

## 修复内容

R9 的手掌配准后采用肩肘解算，部分新增角度集中在腕关节，产生腕部硬折。R10 改为在左锁骨处对整条源手臂做刚体配准；腕、手指、上下臂和辅助骨的局部姿态均保持原配置。V9 网格、rest、权重及源动画文件不修改。

弹匣侧面和背面的近景检查发现拇指穿插。修正通过整手的位置和角度完成，保留四指包住前缘、拇指自然向上的手型。闭合弹匣外包络用于保守避让，实际三角面距离与绕数用于区分真实穿插和开放模型的法向误报。随后将握位沿弹匣脊线下移 2.3 cm，使落座时拇指避开机匣。

配准在源帧 0–20 渐入，保持到手掌离开弹匣后，于 280–302 淡出。接近段另有最大约 6.38 mm 的平滑整臂避让（12–49 帧）。源序列没有重定时，原本的收指、开掌、拔匣、插匣、落座、拉栓和音效接触时钟保留。

## 复查结果

| 项目 | 普通换弹 | 空仓换弹 |
| --- | --- | --- |
| 源姿态采样 | 401 帧 | 516 帧 |
| 实际运行中有效换弹画面 | 22 帧 | 30 帧 |
| 上述画面原生 V9 可见 | 全部 | 全部 |
| 上述画面加载 R10 动作配置 | 全部 | 全部 |
| 持匣期间腕点相对弹匣最大漂移 | 0.0306 mm | 0.0538 mm |
| 相对转角漂移 | 0.0013° | 0.0022° |
| 腕／手指／臂内局部姿态相对原配置误差 | 0 | 0 |
| 换弹结束 | 正常，10 发 | 正常，10 发 |

实际画面逐段复查了接近、拔匣、取新匣、插入、压实、松手回握和空仓拉栓。抓匣段未再看到 R9 的硬折、拇指嵌入或握点滑动。持匣关键帧的实际弹匣表面检查、落座关键帧的机匣检查均未检出手部嵌入。

源帧 12–302 每帧检查覆盖两种换弹，共 582 个弹匣包络采样；保守包络在倒角附近的最大交叠约 0.101 mm。原持枪／护木回握基准中约 2 mm 的局部皮肤贴合保留，不将本次结果表述为整把枪所有顶点绝对零交叠。

首次采样发现原生 V9 异步载入较晚，因此补充了 `NativeV9Ready` 等待条件，未把早期内嵌手臂画面作为最终 V9 证据。最终有效运行是 `Saved/SVCHPoseAudit/svch-reload-r10-seated-final-20261018/`，其中 132 张整体过程截图包含上述 52 张有效换弹画面。

12 条认可的 SVD 源动画和原生 V9 手模共 13 个文件的散列保持不变；R8 枪体、右手配置、另外 10 个动作配置也保持不变。期间出现的外部后台动画批次已退出，最终落盘及复查时重新确认了这些源文件。

## 交付与证据

- UE 配置：`/Game/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip`，内容为 R10；历史目录名不代表回退。
- [普通换弹实际运行预览](../../SourceAssets/SVCHRefinement20261018/R10ReloadReview/reload_normal_review.gif)
- [空仓换弹实际运行预览](../../SourceAssets/SVCHRefinement20261018/R10ReloadReview/reload_empty_review.gif)
- [可编辑 Blender 源](../../SourceAssets/SVCHRefinement20261018/R10ReloadReview/SVCH_R10_ReloadGrip_Editable.blend)
- [保存、源文件保留及运行回执](../../SourceAssets/SVCHRefinement20261018/R10ReloadReview/validation_receipt.json)
- [普通换弹逐帧图](../../Saved/SVCHPoseAudit/svch-reload-r10-seated-final-20261018/reload_normal_contact.jpg)
- [空仓换弹逐帧图](../../Saved/SVCHPoseAudit/svch-reload-r10-seated-final-20261018/reload_empty_contact.jpg)

后台 `FPSGAMEEditor Win64 Development` 构建成功。复查使用独立存档和离屏游戏进程，没有打开交互式编辑器或修改正式存档。范围为原厂弹匣的第一人称普通／空仓换弹；未扩展到全配件组合、联机或音频验收。

重制顺序：`refine_solid_contact.py` → `adjust_receiver_clearance.py` → `author_native_registration.py` → `install_profile.py`。最终接近段参数已固定在 `contact_arcs.json`；修改接近关系时再重新计算该文件。`export_editable.py` 输出武器与原生 V9 两套对应 action。诊断及早期候选保留在本轮源目录，`collect_current_source.py` / `rebase_approved_profile.py` 是未执行的共享源变更预备工具，不属于本次已应用内容。
