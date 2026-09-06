# 添加天气的标准工作流

## 1. 明确天气合同

记录模式ID、中文名、触发条件、持续时间、进入/退出过渡、粒子/云/光/音频表现、室内遮蔽、是否影响玩法，以及是否值得预告。新模式先说明是降雨强度阶段还是独立事件；不要按特效数量创建事件。当前系统不包含闪电伤害、湿度或积水玩法。

现行基线：一天24分钟；晴、阴、小雨、中雨、暴风雨；长期降雨约40%；同场降雨可包含多档强度。手动F6选天气，Shift+F6恢复自动。测试可以立即切换，正式游戏走平滑过渡。

## 2. 接入唯一时间源与调度

| 文件 | 职责/修改点 |
|---|---|
| ui/game_clock.gd | DAY_SECONDS=1440、elapsed_seconds、weather_seed、serialize/restore |
| ui/hud.gd | 每帧推进未暂停时钟，存档保存/恢复game_clock |
| scripts/weather_schedule.gd | day_plan返回mode/start/end，state_at查询实际阶段；预报复用同一计划 |
| scripts/weather_system.gd | NAMES/LABELS/PROFILES注册、set_weather、自动计划到期刷新、resume_automatic |
| scripts/day_night_environment.gd | 世界环境、日月星空、天气节点与10Hz光照更新 |
| scripts/world_lighting.gd | 场景创建公共环境与太阳的入口 |

以weather_seed和游戏日确定计划，不使用逐帧概率抽签。保持有序、正时长、日内完整覆盖；午夜、读档、时间回退和跨场景必须复现相同阶段。新档随机种子，旧档稳定默认值。当前区域共用此时间计划；独立气候需另行设计区域种子键，不能只更改显示名称。

## 3. 制作表现与音频

PROFILES当前Vector3为云量、雨量、风强度。新效果若无法表达，增加明确字段和对应消费端，勿改变已有分量含义。枚举、手动切换、调度、显示名称必须同步。

云层使用assets/environment/weather_clouds.gdshader，云遮光与渲染保持一致；雨量控制现有粒子amount_ratio和音量。场景切换、停雨、暂停应正确停发射/淡出并清理雷声等待状态。屋顶遮蔽是近身射线近似，不宣称完整屋顶粒子碰撞。

素材优先既有管线；正式资源用新版本名验证后接入，保留导入配置。雨声由tools/generate_soft_rain.py生成两层24秒立体声，雷声由tools/generate_wilderness_thunder.py生成三种11秒回响。SOURCE.md记录来源、采样率、循环/非循环和生成入口。试听连续至少两轮循环、各雨量和雨停淡出；雷声试听裂响、延迟、空间声像与尾音是否完整。

## 4. 接入事件进度栏

1. 在ui/event_timeline_model.gd补WEATHER_NAMES/ICONS/IMAGES；有源PNG就复用原PNG并在assets/ui/event-icons/SOURCE.md记来源。不要用近似emoji替代已有正式图标。
2. 当前weather_events从同一个Schedule构造连续降雨过程，仅返回当前或最近将来的一个过程。新增降雨模式时，同步这里两处wet成员判断、手动模式判断及测试；晴/阴不创建事件。
3. 事件字典包含id、type=weather、type_label、label、world_name、mode、at/start/end、status、icon_path、intensity_name、duration_label、warning_level/label。连续强度过程附stages，阶段为mode/start/end。起点生成稳定ID；active取当前实际强度，upcoming显示整体过程和雷暴预警。
4. at/start/end为现实秒绝对时间；HUD模型将其转换为游戏时间与时间轴位置。status为active/upcoming；手动模式用manual并明确无自动未来预报。天气结束后旧事件消失。
5. ui/event_timeline.gd保留原紧凑/展开格式、当前游标、类型筛选、图标点击、Esc关闭及详情滚动。详情说明阶段依次发生，不把阶段交给通用同期事件聚合。其他非天气事件仍通过register_provider接入。
6. 当前场景更换时释放旧天气引用，更新区域名，关闭旧弹窗。小窗口避让时钟，左Alt释放鼠标以点按事件。新模式若只增加表现，不需要新UI卡片或新时间轴。

## 5. 验证与交付

- 隔离INVENTORY_SAVE_PATH，先导入新增资源，再跑tests/test_day_night.gd、test_weather_schedule.gd、test_weather.gd、test_event_timeline.gd；依据改动跑test_weather_hud.gd与test_ui_tokens.gd（开发目录完整主HUD另跑test_main_hud_layout.gd）。
- schedule多日统计时长占比；检查干燥间隔、连续雨上限、跨日、暂停、回退、读档种子恢复。预报遍历多个时刻，对照实际Schedule，验证最多一个天气事件、雨势变但ID不变、雨停更新、手动晴天不入栏。
- 用tests/render_weather.gd看真实场景；tests/render_event_timeline.gd查看1920/1280/960紧凑、展开、详情。强光/暗背景、屋顶内外、各雨量、雨停和雷暴均需观察。用60Hz采样动态预览，不用低帧GIF替代实机验收。
- 性能记录硬件、渲染器、分辨率、预热、相机/场景、样本时长、CPU/GPU帧耗时与粒子量；读回截图基准不能当正常游戏FPS。
- 按WORKFLOW第4、8节做启动、combat/reload、日志检查；区分本次失败与既有夹具问题。

## 6. 清理与Git发布

建立本次明确文件清单。保留最终代码、生成脚本、来源、测试和最终预览；搜索引用后删除已被取代的音频/图片及对应import/UID，不清理全库缓存。原项目来源快照保持不变。旧预览有证据价值则标注历史，不把失败卡片样式继续作为当前标准。

核对origin与用户目标、远端默认分支和上游，fetch后审查所有待推提交。混合历史在基于最新origin/main的独立发布工作区处理；共享HUD只提取本次接线，不能整文件带入其他未发布系统。检查暂存文件、完整差异、diff --check、资源依赖及大文件。普通非强推，非快进先更新基线，推送后用ls-remote回读SHA。发布说明明确本次文件和未包含的并行改动。
