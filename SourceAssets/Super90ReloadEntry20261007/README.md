# Super90 空仓换弹移除检视前摇

用户要求：空仓换弹去掉前面类似查看的动作，并询问该枪的空仓枪机操作。

原因：末发播放 `A_Super90_fire_last`，源为 `M4_Fire_LastRoundCheck`，整条长 2.15 秒。原制作脚本从第 22 帧开始抽取独立 Inspect；运行时却把整条当作末发动作，`BeginSuper90Reload` 等待它全部结束才开始换弹。

修改 `FPSGAMECharacter.cpp::PlayWeaponAnimation`，仅对 Super90 末发动作把播放窗口截止到 22/60 秒，继续沿原 ActionAlpha 收势。末发动作和换弹等待使用同一个 LastShotWorldTime 时钟；随后沿现有流程直接进入侧倾连续填弹。主动 Inspect 序列、逐发补弹时钟、循环打断、机械声音与末尾枪机操作不变。

此改动仅限制原序列的运行播放窗口，不重定时或覆盖骨骼轨道。原厂及通用握把差量仍按同一原始时间采样，无须重制资产。

实际 M4 的相关部件是侧面拉机柄、枪机及释放机构，不是手枪套筒。官方手册第 60–62 页区分直接向弹膛装填和从管仓供弹的方式。本轮保留现有末尾上膛动作，不宣称已重做为另一套真实操作顺序。

来源：https://www.benelliusa.com/sites/default/files/content/media/manuals/2019-10/M4%20Tactical%20Shotgun%20Product%20Manual.pdf

按用户规则仅后台制作和必要编译，不启动游戏、测试、截图或渲染。
