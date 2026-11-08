# 锥形锤座改造图标 V2

2026-11-09 整理：原 Before/ 的 V1 PNG/uasset 已移入 trash/ConversationCombat20261109/SourceAssets/ConicalHammerSeat20261107/IconV2/Before；认可成图和灰模参考均保留。

2026-11-07。用户否定 BuildV1 图标后，按改造配件图标标准重新生成。

用户随后明确认可本版图标，并授权玩法接入；相关交付记录见 `../IntegrationV1/README.md`。本版继续作为通用共享母图。

本版使用内置 imagegen。边框参考为已认可的 `SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png`；主体参考为实际模型制作出的 `BuildV1/Icons/conical_seat_actual_gray.png`。完整生成提示词保存在 `generation-prompt.txt`。

成图 `head_mount_conical_seat.png` 使用厚倒角钢框、四角铆钉、厚银色内环和凹陷深色底板；保留锥形锤座实际轮廓、向左的尖锥、四颗紧固件、双折线凹槽及上下承力边。强调银灰金属的切面、粗糙度与凹槽层次，替代被否定版本的亮灰底板和过曝主体。

共享运行 PNG：`Content/ColdSteelData/AttachmentIcons20260913/head_mount_conical_seat.png`。

UE 纹理路径保持：`/Game/Weapons/CommonHammerSeats20261107/ConicalSeatV1/head_mount_conical_seat`。导入 UI 纹理组、Editor Icon 压缩、sRGB、Never Stream、No Mipmaps，最大纹理尺寸 1024。实际保存结果见 `import_receipt.json`，共享 PNG 替换记录见 `publication.json`。

旧 PNG 和 UE 纹理保存在 `Before/`；BuildV1 制作历史不删除。以后重建图标使用本版提示词及上述双参考，不能重新发布已被否定的 Blender 自制框图。

本次仅替换图标；模型、材质、玩法状态未改变。未运行游戏测试，外观由用户确认。
