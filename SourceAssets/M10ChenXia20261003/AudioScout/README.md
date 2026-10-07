# 沉匣 M-10 音效候选筛选（公开渠道）

2026-10-04 搜索整理。目标：为 M10（宽体八足、眼口组织、腹腔共鸣腔体、扇形嚎叫、毒雾、撕咬）收集可合法用于公开仓库游戏的怪物音效。

## 需要的音效事件（来自 Docs/Monsters/M10Mawcrawler.md 动作合同）

| 事件 | 时序要求 | 说明 |
|---|---|---|
| Idle 呼吸/腹腔共鸣 | 3.2 s 循环 | 躯干轻呼吸，低频共鸣腔体感（"沉匣"身份） |
| Walk 八足爬行 | 1.2 s 循环 | 湿肉足垫错相落地 + 组织摩擦层 |
| Bite 合咬 | 0.70 s 接触点 | 颌部咬合 + 前冲低吼 |
| Howl 扇形嚎叫 | 0.6 s 前摇 + 3 s 释放 + 0.6 s 收势 | 当前复用 S_HandBrain_howl，SAN/致残挂钩，需更贴合身份 |
| 毒雾释放 | 6 s 释放 + 8 s 保持 | 臀部出气口，湿嘶声而非纯气罐 |
| 受击 Hit | 0.667 s | 肉质受击反应 |
| 死亡 Death | 2.5 s，60% 交物理 | 倒地闷响 + 咽气 |
| 警觉/追击吼 | 触发式 | 发现目标时的吼叫 |
| 环境回声 | 循环底床 | 地牢/洞穴反射（也可用 UE 混响而非烘焙） |

## 已下载可试听预览（Previews/，mp3 仅供试音）

全部为 **CC0**，无需署名、可商用、可修改、可进公开仓库。

| 文件 | 时长 | 用途匹配 | 源 |
|---|---:|---|---|
| 479380_breviceps_dragon_roars_60s | 60 s | 吼叫/嚎叫素材库：多段吼、咆哮、嘶吼，可裁出 3 s 嚎叫和警觉吼 | freesound.org/s/479380 (Breviceps) |
| 466830_breviceps_dragon_snarl_roar_attack_3s | 3.3 s | 撕咬前冲吼/警觉吼一击 | freesound.org/s/466830 |
| 621005_samsterbirdies_deep_scary_growl_9s | 9 s | 洞穴低吼，可作警觉或死亡咽气底层 | freesound.org/s/621005 |
| 431527_hgsbsn_monster_rumble_8s | 7.6 s | 腹腔共鸣 + 自带洞穴混响，贴合"沉匣" | freesound.org/s/431527 |
| 368255_mburgess1_deep_growl_cave_5s | 5 s | 洞穴低吼，回声感天然 | freesound.org/s/368255 |
| 844096_perspektywa_heavy_breathing_beast_7s | 7 s | 沉重兽息，Idle 呼吸层主料 | freesound.org/s/844096 |
| 695999_samanthacastleberry_stomach_growls_61s | 61 s | 连续低频腹鸣/肠鸣，裁段做腹腔共鸣循环和随机肚鸣层 | freesound.org/s/695999 |
| 635042_sillygrizzlies_blood_gush_squelch_51s | 51 s | 西瓜瓤挤压的血肉湿滑声，组织摩擦/受击主料 | freesound.org/s/635042 |
| 834075_federicoy_wet_slimy_movement_96s | 96 s | 生鸡肉搅动的湿足步与快慢移动，八足爬行主料 | freesound.org/s/834075 |
| 467701_lucasduff_monster_bite_2s | 2 s | 巨口咬入血肉，合咬点 | freesound.org/s/467701 |
| 421826_kinoton_dark_cave_drone_257s | 257 s | 低频洞穴声景（雷鼓合成），地牢氛围底床 | freesound.org/s/421826 |

## 已下载 OGA 包（OGA_Packs/，可直接使用）

- `monster_roar.wav`（1.3 MB，CC0）：为巨型沙虫设计，适合嚎叫底层或远处吼声。opengameart.org/content/cc0-deep-monster-roar
- `80-CC0-creature-SFX.zip` + `80-CC0-creature-sfx-2.zip`（rubberduck，CC0，160 个 ogg）：含 roar/monster/slime/die/hurt/breath/stomp/spit 分类。多为小型卡通感怪声， slime_01-08 可做组织摩擦补充，monster_15-20 体型较大可试听挑选，die_01-04 可配死亡。
  - opengameart.org/content/80-cc0-creature-sfx
  - opengameart.org/content/80-cc0-creture-sfx-2

## 备选（CC-BY，需署名后才能用；已核证未下载）

| 候选 | 许可 | 用途 |
|---|---|---|
| freesound.org/s/796506 KVV_Audio 血肉揉捏 8.8 s | CC-BY 4.0 + 作者要求署名 | 组织摩擦备选 |
| freesound.org/s/347710 TinTinOko 洞穴怪物叹息 5 s | CC-BY 3.0 | 呼吸/回声备选 |
| freesound.org/s/555745 MGA95 气压释放 9.9 s | CC-BY 4.0 | 毒雾喷射备选 |
| freesound.org/s/231550 zerolagtime 喷射短爆 3.1 s | CC-BY 4.0 | 毒雾首喷备选 |

## 已排除

- **BBC Sound Effects 库**：RemArc 许可限个人/教育/研究，不能进游戏。
- **ZapSplat**（136 个怪物包 + 黏液怪包）：质量高但需注册账号，免费档要求署名或付费；原文件再分发受限。如用户已有账号可再评估。
- **Pixabay SFX**：需账号下载；内容许可禁止原样再分发裸文件，进公开 Git 有争议，暂不作主源。
- **Freesound CC-BY-NC 条目**（如 Artninja 咬击混音引用了 NC 源）：非商业不可用，一律排除。
- **itch.io 付费/免署名包**（AlesiaDavina 100 怪声、PixelLoops 93 恐怖包等）：可商用但 "name your price" 付费门槛，且禁止再分发裸文件；只有用户愿意购买时才考虑。

## 下一步

1. ~~试听 Previews/ 下 11 个 mp3 和 OGA_Packs 解压音频，标记采纳/否决。~~ 已按用户确认接入（V1 见 `../AudioV1`）：犬息 844096 被否决（犬类音色），待机改用腹腔共鸣；其余 8 个 freesound CC0 源全部投入使用，OGA 包留作备选库。
2. 采纳的 freesound 条目：正式 WAV 需 freesound 免费账号下载（预览 mp3 质量不够做成品）；下载页 URL 见上表 `s/<id>` 格式。拿到 WAV 后放回原路径重跑 `../AudioV1/prepare_audio.py` 即可无损替换。
3. 回声建议走 UE 侧：嚎叫干声 + 衰减/混响（reverb volume 或 sound cue send），比烘焙尾巴更随场景自适应；431527 自带混响可作对照。V1 保留烘焙混响尾，未做引擎侧混响配置。
4. 制作管线沿用现有：ffmpeg/imageio_ffmpeg 或 numpy 切片调音 → `prepare_audio.py` → commandlet 导入 `Content/Monsters/M10Mawcrawler/Audio`，命名 `S_M10_<事件>`；来源记录写入 `audio_source.json`（含 CC0 声明与链接）。
