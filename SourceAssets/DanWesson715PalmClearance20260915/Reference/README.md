# 左轮参考动作来源

来源为 https://github.com/ZenXChaos/ThirdPersonShooter-AnimationSets ，固定提交 `f19adc2ece4cab0f89c9236223abb97d4d2badea`，仓库声明 Unlicense。原始 FBX、许可和来源散列保留在 `SourceAssets/DanWesson715Upgrade20260914/Reference`。

使用 `RevolverReloadInit` 的手指方向作为参考：30 fps、1–25 帧、0.8 秒，采用第 10.5 帧（0.316667 秒）的姿态。该来源不包含与 DW715 完全一致的退壳按压接触；当前接触和腕肘支撑由本枪作者脚本适配。

原始 FBX 具有蒙皮顶点但无面索引。此前资料学习使用点云和骨段，图片与旧制作记录已随 DonorPress 移到 `trash/pistol-animation-20260915/SourceAssets/DanWesson715DonorPress20260915`，不作为完整网格或本次效果证明。当前制作直接读取上游 `donor-poses.json`，不依赖归档目录。
