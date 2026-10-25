#pragma once

#include "CoreMinimal.h"
#include "../../Combat/MonsterToughnessTypes.h"

/**
 * 尼泊尔弯刀（Kukri）作者动作时钟。所有数值都是作者秒（120 fps 源、30 fps 重采样网格），
 * 运行时统一乘以同一个播放速率；命中窗、挥空声、镜头曲线与顿帧共用这一条时钟。
 *
 * 第一段逐帧复刻 BV1CeYUeSE7b 1:27.00-1:28.27（近战 #2 从右到左大范围横挥），V11 第二段逐帧复刻
 * 1:24.33-1:25.60（近战 #1 左上→右下斜劈）。作者源：SourceAssets/Kukri20261020/fit_reference.py →
 * attack_keys.json / attack2_keys.json / attack3_keys.json → author_kukri_clips.py（clip "Attack" / "Attack2" / "Attack3"）。
 */
namespace KukriRhythm
{
    inline const TCHAR* Folder=TEXT("/Game/Weapons/Kukri20261020/Animations/");
    inline const TCHAR* ArmsMesh=TEXT("/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms.SK_FrostSword_Arms");
    inline const TCHAR* BladeMesh=TEXT("/Game/Weapons/Kukri20261020/SM_Kukri.SM_Kukri");

    /** 第一段 clip 作者长度（38/30 s）；物品 attack_seconds = 1.5625 倍（V9、V10 各慢 25%），攻速只缩放这一条时钟。 */
    inline constexpr float AttackSeconds=38.f/30.f;
    inline constexpr float EquipSeconds=.70f;
    /** 进入／切换 clip 的局部空间交叉淡化（保持右手相对刀柄）。 */
    inline constexpr float EntryBlendSeconds=.11f;
    inline constexpr float SprintBlendSeconds=.18f;

    /** 第一段相位（作者秒，V6 水平横劈）：
     *  0.00-0.10 刀身放平、向右上蓄势；0.13-0.23 胸口高度向右外侧打开出画（画外转掌心朝上）；0.27-0.30 刀把领先从右侧切入；
     *  0.33-0.43 拳心同一高度横扫过画面，刀身放平指向前方、刃口向左领先（命中）；0.50-0.70 继续向左偏下出画；
     *  0.77-0.97 落出画面；1.03-1.27 由下抬回、翻刀入待机。 */
    inline constexpr EMonsterAttackForm Form=EMonsterAttackForm::Blade;

    /**
     * 三段连击（V11，2026-10-22）：段与段之间按双手剑的节奏留出攻击间隔——每段都完整播到回到架势，
     * 命中窗结束后的点击才缓冲（每段一次），本段回到架势的那一刻直接起下一段；未缓冲时回待机，
     * 0.85 s 内再点仍接下一段，超过则从第一段重来（与双手剑 NextSlash 规则相同）。三段都从架势起手、回到架势收尾。
     *  第一段 Attack（右→左，上述相位，1.267 s）。
     *  第二段 Attack2（V11 左上→右下斜劈，1.267 s，逐帧复刻参考 1:24.33-1:25.60 近战 #1）：
     *    0.03-0.10 刀身向左下压平、拳落到画面下方正中；0.13-0.33 反手蓄势——拳贴近镜头由下向左上横过画面，
     *    停在左缘地平线附近，刀身向左上伸出；0.33-0.47 一次斜劈穿过画面中心到右下角出画，刀身拖在拳后指向左上
     *    （命中 0.34-0.47，挥空声 0.31）；0.50-0.95 画外；1.03-1.27 抬回、翻刀入架势（与第一段收尾同一动作）。
     *  第三段 Attack3（V12 单手低位戳刺，1.267 s，逐帧复刻参考 1:34.77-1:35.97 近战(蹲) #5 戳）：
     *    0.03-0.10 刀身翻立、拳落到画面下方正中；0.13-0.17 拳滑到左下、刀尖转向前方；0.17-0.33 收在左胯蓄力，
     *    刀尖悬在准星下方；0.33-0.37 一帧刺出——拳由左下直抵准星，前臂从左下伸入，刀身指向画面深处（命中 0.34-0.47，
     *    挥空声 0.31；V12c 起定格 0.30-0.333、0.367 到点硬停并过冲回弹，挥空声 0.328）；0.40-0.533 停在准星上；0.60-0.77 向左下收回、刀身竖起从画面下方出画；0.78-0.90 画外回转前臂，0.90-1.27 刀身从画面下方竖起、向左放平，抬回入架势（与第一段收尾同一组目标）。
     * 三段同伤害、同播放速率（物品攻速）；三段作者长度都是 38/30 s（参考第三段 1.17-1.2 s 回到架势，收尾沿用第一段的抬回节奏）。
     * 第一段镜头 = 参考 #2 配准曲线；第二段镜头 = 参考 #1 配准曲线（DiagYaw…，蓄势左转抬头、逆时针滚，劈下时右甩、
     * 顺时针滚并放宽视场）；第三段镜头 = 参考 #5 远景配准曲线（Stab…）加前冲位移。左手全程不出画。
     */
    struct FSwing
    {
        const TCHAR* Clip;
        float Length,SwingSound,ContactStart,ContactEnd;
        float BufferOpen;       // earliest author time a click is buffered (two-handed cadence: after the contact)
        float SwingPitch;
        float CameraPitchScale; // reference curves: V6 keeps the first sweep level (0.4); the diagonal keeps 0.7 of its lift
        int32 CameraMode;       // 0 = melee #2 sweep curve, 1 = melee #5 stab curve, 2 = melee #1 diagonal curve, 3 = #9 uppercut,
                                // 4 = #12 heavy release (starts on the loaded charge camera, KukriHeavyRhythm)
        float CameraGain;       // per-stage swing camera amplitude on top of CameraScale
        float HitStopScale;     // flesh hit-stop multiplier (V9: the thrust lands heavier)
        float ImpactScale;      // hit shake / FOV punch multiplier
        float KickYaw,KickPitch;// viewmodel impact kick: pushed back against the travel (+yaw right, +pitch up)
        float HitRoll;          // confirmed-hit camera roll rattle on top of ImpactScale (V12 stab: the reference rattles ~+-6 deg)
    };
    inline constexpr int32 SwingCount=3;            // the left-click combo: stages 0-2
    /** Stage 3 = the uppercut (swordUppercut skill, KukriUppercut.cpp), stage 4 = the heavy release (heavyStrike skill,
     *  KukriHeavy.cpp, KukriHeavyRhythm.h): same tables, outside the combo. */
    inline constexpr int32 UppercutStage=3, HeavyStage=4, StageCount=5;
    inline constexpr FSwing Swings[StageCount]={
        {TEXT("Attack"), 38.f/30.f,.27f, .32f,.45f,.45f,.96f, .4f,0,1.f, 1.4f,1.f,  1.f,-1.f,1.f},
        {TEXT("Attack2"),38.f/30.f,.31f, .34f,.47f,.47f,1.04f,.7f,2,1.3f,1.5f,1.15f,-1.f, 1.f,1.f},
        {TEXT("Attack3"),38.f/30.f,.328f,.34f,.47f,.47f,1.15f,1.f,1,1.f, 2.0f,1.25f,-1.f,-1.f,2.2f},
        {TEXT("Uppercut"),38.f/30.f,.29f,.30f,.433f,1.f,.95f,1.f,3,1.f, 2.2f,1.4f,-.6f,-1.f,1.8f},
        // Heavy release (V2 back-chop): the cut runs 0.033-0.133 (blade over the top -> fist out at the lower left); a hit
        // stops it hard and pushes it back up-right.
        {TEXT("HeavyRelease"),35.f/30.f,.010f,.033f,.133f,1.f,.85f,1.f,4,1.f, 3.0f,2.0f,1.f,1.f,2.6f},
    };

    /**
     * 打击时刻（V12c 第三段，V12d 推广到前两段；运行时 KukriStrike.cpp）。At 之前查到的目标伤害即时结算，命中音、顿帧、
     * 血雾压到 At 再出；到 At 时无论是否命中都给一下真实时间的镜头冲击，挥空时动作再硬停 MissStop。
     *  第一段横劈：At = 刀身扫过画面中心（0.357），镜头跟着刀向左一带、略前冲；命中时视模顺着劈向往左带 1 cm。
     *  第二段斜劈：At = 刀身扫过画面中心（0.380），镜头向右下一带；命中时视模往右下带。
     *  第三段戳刺：At = 刀尖到准星（0.367），镜头前推、视场放宽、轻抬头；命中时视模向前压 1.2 cm。
     *  重击（第 4 段，V2 回砍）：At = 刀尖劈过准星（0.075，刃口领先 0.94），挥空停 0.05 s，镜头顺着劈向往左下一带、
     *   前冲 3.5 cm、视场放宽 3°；命中时视模顺劈向往左下压。
     */
    struct FStrike
    {
        float At;                          // author time of the impact moment (0 = none)
        float MissStop;                    // real seconds the swing freezes there on a miss (a confirmed hit uses the flesh hit-stop)
        float AccentFov,AccentPushCM;      // real-time camera accent at the impact moment: FOV widening (deg), push forward (cm)
        float AccentPitch,AccentYaw;       // and a nod (+up / +right, deg) along the strike
        float PressX,PressY,PressZ;        // viewmodel push through a confirmed hit-stop (cm, camera: +X forward, +Y right, +Z up)
        bool bWhoosh;                      // stab whoosh instead of the item swing sound
    };
    inline constexpr FStrike Strikes[StageCount]={
        {.357f,.025f, 1.0f,1.0f, 0.f, -.8f,  0.f,-1.0f,0.f,  false},
        {.380f,.025f, 1.0f,1.0f, -.6f, .6f,  0.f, .7f,-.7f,  false},
        {.367f,.035f, 1.5f,2.5f, .6f,  0.f,  1.2f,0.f, 0.f,  true},
        {.350f,.040f, 1.5f,2.0f, 1.0f,-.5f,  .4f,-.5f,1.2f,  true},
        {.075f,.050f,3.0f,3.5f,-2.0f,-1.0f,  .4f,-1.2f,-1.4f,true},
    };

    /**
     * V12c 第三段顿挫与打击感（用户：还是太快，缺顿挫和力度；不加击退）。作者键：蓄力末尾向左下、贴身拉回并定格（0.30-0.333），
     * 0.333→0.367 一次加速刺到准星（越刺越快、到点硬停），随后拳沿刺向过冲 2 cm 再弹回，0.40-0.533 停在准星上。
     * 运行时（KukriStrike.cpp）：刀到点那一刻（Strikes[2].At）无论是否命中都硬停 MissStop（0.035 s），并给一下真实时间的镜头冲击
     * （视场放宽、前推、轻微抬头，30 ms 起、约 0.15 s 落）；刺出途中先查到的目标，命中音、顿帧、血雾都压到到点那一刻再出，
     * 伤害照常即时结算。确认命中顿帧 ×2.0（0.15 s），顿帧期间视模向前压 1.2 cm 再松开。V12d 起这套打击时刻推广到三段（见 FStrike）。
     */
    inline constexpr float StrikeKick=.5f;            // ImpactKick of the miss stop (shake / FOV punch / viewmodel kick)
    inline float StrikeEnvelope(float Age)
    {
        if(Age<0.f)return 0.f;
        if(Age<.03f)return FMath::InterpEaseOut(0.f,1.f,Age/.03f,2.f);
        return FMath::Exp(-(Age-.03f)*16.f);
    }
    /** Stab whoosh on the drive (stage 3); a low flesh thud under the item hit sound on every stage (untested by ear). */
    inline const TCHAR* StabWhoosh=TEXT("/Game/FreeGameSoundsVol1/SFX/Sword_Swing_Medium/Sword_Swing_Medium_01.Sword_Swing_Medium_01");
    inline const TCHAR* StabThud[3]={TEXT("/Game/Weapons/GunplayFX/Impacts/S_Impact_Flesh_0.S_Impact_Flesh_0"),
        TEXT("/Game/Weapons/GunplayFX/Impacts/S_Impact_Flesh_1.S_Impact_Flesh_1"),TEXT("/Game/Weapons/GunplayFX/Impacts/S_Impact_Flesh_2.S_Impact_Flesh_2")};
    inline constexpr float StabWhooshVolume=.6f, StabThudVolume=.75f, StabThudPitch=.78f;

    /**
     * 挥砍剑气 / 空间扰动（2026-10-23，用户：像双手剑一样）。复用双手剑普通挥砍的 M_RuneRift 折射材质：
     * 刀身在打击窗口里的作者轨迹烘成弧形带（KukriRiftRibbons.h，由 SourceAssets/Kukri20261020/author_kukri_rift.py 生成，
     * 视模网格空间 cm），窗口开始时冻结在视模当前的世界变换上，随作者时钟沿弧展开（SweepProgress，顿帧时一起停），
     * 窗口结束后在真实时间里溶解，同时沿镜头前方漂出（与双手剑 StartRift/TickRift 同一做法）。
     * 只给本地玩家看，命中与否都出。戳刺为两条交叉的窄带，沿刀尖前方一点的轨迹。
     */
    struct FRift
    {
        float Start,End;        // author seconds of the reveal (= the ribbon's baked window)
        float Strength;         // M_RuneRift RiftStrength (rune sword: slash .085, thrust .10, heavy .14)
        float Dissolve;         // real seconds of the fade after End
        float DriftCM;          // drift along the camera forward (cm/s, real time)
    };
    inline constexpr FRift Rifts[StageCount]={
        {.290f,.450f,.080f,.20f,85.f},
        {.358f,.470f,.080f,.20f,85.f},
        {.333f,.395f,.095f,.16f,50.f},
        {.290f,.395f,.100f,.24f,95.f},
        {.040f,.133f,.150f,.32f,120.f},     // heavy: a little above the rune sword's heavy (.14), from the blade entering the top
    };
    inline const TCHAR* RiftMaterial=TEXT("/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift.M_RuneRift");
    /** Idle time after a swing that still continues the combo (same as the two-handed swords). */
    inline constexpr float ComboResetSeconds=.85f;

    struct FTempoKnot{float T,Rate;};
    /**
     * 速度（用户：快得几乎看不清）：V9 慢 25%，V10 再慢 25%——物品 attack_seconds = clip 作者长度 × 1.5625，
     * 三段基础播放速率 0.64（第一段、第二段各 1.98 s，即一段完整攻击间隔 = attack_seconds ÷ 攻速，与双手剑同口径）。
     * V12b 第三段戳刺（用户：太快，看不清动画细节）：在基础速率上再乘一条平滑分相时钟 StageTempo，动作键不变。
     * 相邻节点速率不同时用 SmoothStep 过渡，不出现速度台阶（V9 的 PhaseRate 是硬切）。实际秒数（无攻速加成）：
     *  翻刀到左胯 0.00-0.167 ×0.60 → 0.45 s（原 0.27 s，刀身峰值转速 1080 → 650°/s）；
     *  左胯蓄力 0.17-0.31 ×1.0 → 0.26 s（原本就是停顿，保持）；
     *  刺出 0.33-0.40 ×0.55 → 拳到准星约 0.08 s、整段 0.28 s（原 0.16 s，拳峰值 15 → 8.3 NDC/s，仍快于其余各段）；
     *  准星上停顿 0.42-0.56 ×0.60 → 0.37 s（原 0.22 s）；向左下收回 0.59-0.76 ×0.80 → 0.41 s；
     *  画外回转 0.79-0.89 ×1.50（看不见的部分加快）；刀身从画面下方竖起、向左放平 0.93-1.06 ×0.65 → 0.28 s；之后 ×1.0 回到架势。
     * 第三段整段约 2.59 s（原 1.98 s）。命中窗、挥空声、镜头曲线与动作共用这一条时钟，一起拉伸；命中顿帧 ×1.6、冲击 ×1.25 保留。
     * V12c（用户：还是太快、缺顿挫）：改为快慢对比。可见的准备动作慢，出手快：翻刀到左胯 ×0.60（0.45 s）→ 蓄力 ×1.0 →
     * 向左下拉回 ×0.55（约 0.12 s）→ 定格 ×0.50（0.10 s）→ 刺出 ×0.90（0.074 s，拳峰值约 27 NDC/s，前后几乎静止）→
     * 过冲回弹 ×0.90（0.04 s）→ 准星上停顿 ×0.75（0.27 s）→ 拔刀 ×0.55（0.19 s）→ 收回 ×0.85 → 画外 ×1.5 → 收尾同 V12b。
     * 整段约 2.55 s（不含顿帧）。各段时长由 SourceAssets/Kukri20261020/Work/tempo_plan.py 用同一组节点积分核对。
     * V12d 前两段同样改为快慢对比（作者键不变，Work/tempo_plan_all.py 核对）：
     *  第一段横劈：可见的放平蓄势 ×0.70（0.28 s，原 0.20 s）→ 画外右侧蓄力 ×0.80 → 切入 ×1.0 → 横扫过画面 ×1.25（0.19 s，原 0.23 s）→
     *   前臂贴镜头横过的收势 ×0.75（0.52 s，原 0.39 s，减速看得见）→ 画外 ×1.4 → 抬回 ×1.0。整段约 2.05 s。
     *  第二段斜劈：压刀 ×0.75 → 反手蓄势 ×0.90 → 左上顶点定格 ×0.50（0.10 s，原 0.05 s）→ 斜劈 ×1.20（0.15 s，原 0.18 s）→
     *   拖刀出画 ×0.80 → 画外 ×1.3 → 抬回 ×1.0。整段约 1.96 s。
     */
    inline constexpr FTempoKnot SweepTempo[]={{0.f,.70f},{.110f,.70f},{.140f,.80f},{.230f,.80f},{.250f,1.f},{.290f,1.f},
        {.305f,1.25f},{.430f,1.25f},{.460f,.75f},{.680f,.75f},{.710f,1.40f},{.950f,1.40f},{.990f,1.f}};
    inline constexpr FTempoKnot DiagTempo[]={{0.f,.75f},{.110f,.75f},{.140f,.90f},{.285f,.90f},{.300f,.50f},{.328f,.50f},
        {.336f,1.20f},{.445f,1.20f},{.460f,.80f},{.520f,.80f},{.545f,1.30f},{.950f,1.30f},{.990f,1.f}};
    /**
     * 上挑（技能 swordUppercut，2026-10-23）：参考 #9 上撩自带的节奏偏快，同样做快慢对比（Work/tempo_plan_upper.py 核对）：
     *  翻刀下压 ×0.75（0.18 s）→ 右下画外蓄力 ×0.70、蓄满前再慢一拍 ×0.55（0.23 s）→ 上撩 ×1.0（参考原速，拳由右下穿过画面中心，
     *  0.30-0.43 → 0.13 s；参考自身拳速约 22 NDC/s，本作前臂贴近镜头时更快）→ 前臂贴镜头的收势 ×0.70（0.37 s，看得见的上举与停顿）→
     *  画外 ×1.4 → 抬回 ×1.0。整段约 1.42 s（武技时钟：不随攻速，只受迅捷影响）。
     */
    inline constexpr FTempoKnot UpperTempo[]={{0.f,.75f},{.130f,.75f},{.160f,.70f},{.250f,.70f},{.270f,.55f},{.290f,.55f},
        {.302f,1.f},{.430f,1.f},{.450f,.70f},{.690f,.70f},{.720f,1.40f},{.950f,1.40f},{.990f,1.f}};
    /**
     * 重击出手（技能 heavyStrike，2026-10-24）。V2（用户：出手更快、更有冲击力）：蓄力已经把刀压在肩后，出手直接回砍，
     *  刀从头后翻过 ×1.0（0.03 s）→ 劈过画面 ×1.6（松手后约 0.056 s 刀尖到准星，0.077 s 拳到画面下方，拳峰值约 38 NDC/s，
     *  比戳刺还快）→ 到点硬停（挥空 0.05 s、命中顿帧 ×3.0）→ 下方收势 ×0.9 → 画外 ×1.7 → 抬回 ×1.0。整段约 0.88 s
     *  （不含顿帧；武技时钟：不随攻速，只受迅捷影响）。V1 先向右上提刀出画再劈，松手到准星约 0.17 s。
     */
    inline constexpr FTempoKnot HeavyTempo[]={{0.f,1.f},{.025f,1.f},{.035f,1.60f},{.135f,1.60f},{.150f,.90f},{.200f,.90f},
        {.230f,1.70f},{.780f,1.70f},{.820f,1.f}};
    inline constexpr FTempoKnot StabTempo[]={{0.f,.60f},{.150f,.60f},{.185f,1.f},{.225f,1.f},{.245f,.55f},{.295f,.55f},
        {.302f,.50f},{.331f,.50f},{.336f,.90f},{.400f,.90f},{.410f,.75f},{.525f,.75f},{.540f,.55f},{.590f,.55f},{.610f,.85f},
        {.760f,.85f},{.785f,1.50f},{.890f,1.50f},{.930f,.65f},{1.060f,.65f},{1.110f,1.f}};
    template<int32 N> inline float SampleTempo(const FTempoKnot (&K)[N],float T)
    {
        if(T<=K[0].T)return K[0].Rate;
        for(int32 I=1;I<N;++I)
            if(T<K[I].T)return FMath::Lerp(K[I-1].Rate,K[I].Rate,FMath::SmoothStep(K[I-1].T,K[I].T,T));
        return K[N-1].Rate;
    }
    /** Stage-local tempo on top of the swing's play rate at author time T (1 = authored rhythm). */
    inline float StageTempo(int32 Stage,float T)
    {
        return Stage==0?SampleTempo(SweepTempo,T):Stage==1?SampleTempo(DiagTempo,T):Stage==2?SampleTempo(StabTempo,T):
            Stage==HeavyStage?SampleTempo(HeavyTempo,T):SampleTempo(UpperTempo,T);
    }
    inline constexpr float CameraCarrySeconds=.18f;
    inline constexpr float CameraTailSeconds=.15f;

    /** 刀身局部点（cm，SM_Kukri 握点坐标：+Z 刀身、+X 刃口）。 */
    inline const FVector BladeRoot(0.6f,0.f,8.f);
    inline const FVector BladeMid(2.5f,0.f,16.f);
    inline const FVector BladeTip(6.18f,0.f,26.29f);

    /** 起点在刀身附近的前向区域查询：半径与快速近战同量级，射程取物品 melee_reach_cm。 */
    inline constexpr float QueryRadiusCM=26.f;
    inline constexpr float DefaultReachCM=150.f;

    /** 命中顿帧（真实秒）：动作、命中窗与镜头曲线同时冻结，期间视模细颤。 */
    inline constexpr float FleshStopSeconds=.075f;
    inline constexpr float WallStopSeconds=.08f;
    inline constexpr float ImpactKick=1.6f;

    /**
     * 挥刀镜头曲线：参考视频背景特征点逐帧配准（Saved/Reference/KukriBV1CeYUeSE7b20261020/
     * camera_atk2.py → atk2_camera.json）换算到本作 75° 垂直视场的屏幕位移，30 Hz 采样，单位度。
     * Yaw + 向右、Pitch + 抬头、Roll + 顺时针（UE），Fov 为垂直视场增量。
     * 蓄势时镜头轻微右转低头收窄视场；0.333 s 出刀瞬间约 14° 翻滚冲击并反向回摆；
     * 横扫后镜头被带向左上约 10°/6°、视场放宽约 5.5°，约 0.9 s 回正。
     */
    inline constexpr int32 CameraSamples=39;
    inline constexpr float CameraYaw[CameraSamples]={0.00f,1.20f,2.24f,2.90f,3.11f,3.01f,2.56f,1.49f,0.02f,-2.02f,-3.71f,-4.07f,-5.60f,-8.24f,-9.68f,-10.14f,-9.88f,-9.36f,-8.37f,-6.49f,-4.94f,-4.06f,-3.08f,-2.14f,-1.50f,-0.90f,-0.38f,-0.08f,0.10f,0.15f,0.10f,0.09f,0.19f,0.26f,0.28f,0.21f,0.07f,-0.01f,0.00f};
    inline constexpr float CameraPitch[CameraSamples]={0.00f,-0.95f,-1.92f,-2.58f,-2.80f,-2.75f,-2.50f,-1.98f,-1.34f,-0.12f,2.19f,4.59f,5.97f,6.12f,5.30f,3.87f,2.37f,1.42f,0.88f,0.30f,-0.32f,-0.78f,-1.13f,-1.36f,-1.45f,-1.41f,-1.24f,-1.07f,-0.85f,-0.56f,-0.30f,-0.07f,0.09f,0.14f,0.07f,-0.02f,-0.01f,0.02f,0.00f};
    inline constexpr float CameraRoll[CameraSamples]={0.00f,0.31f,0.42f,0.53f,0.14f,-0.37f,-0.74f,-0.67f,0.12f,0.74f,13.95f,-5.27f,-6.19f,0.33f,1.10f,2.79f,4.16f,4.21f,4.10f,2.14f,0.96f,0.99f,0.39f,0.03f,0.03f,-0.08f,-0.14f,-0.16f,-0.12f,-0.12f,-0.25f,-0.36f,-0.34f,-0.02f,0.50f,0.72f,0.42f,0.08f,0.00f};
    inline constexpr float CameraFov[CameraSamples]={0.00f,-0.86f,-1.38f,-1.68f,-1.91f,-1.98f,-1.90f,-1.81f,-1.36f,0.19f,2.10f,3.32f,4.62f,5.50f,4.76f,3.29f,2.24f,1.74f,1.01f,0.11f,-0.31f,-0.51f,-0.35f,-0.05f,-0.27f,-0.56f,-0.71f,-0.76f,-0.66f,-0.52f,-0.26f,0.01f,0.19f,0.16f,0.01f,-0.06f,-0.01f,0.03f,0.00f};
    /**
     * 第二段（V11 斜劈）镜头：参考 #1（1:24.33-1:25.60）背景配准（SourceAssets/Kukri20261020/Reference/camera_atk1.py →
     * atk1_camera.json → curve_atk1.py），按第一段曲线的同一换算比例写成 30 Hz，三点平滑去掉参考命中时的逐帧滚转抖动
     * （确认命中另有 HitShake）。蓄势时左转约 1.8°、抬头约 1.3°、逆时针滚约 3.7°；出刀瞬间右甩，劈下时顺时针滚到约 4.4°、
     * 视场放宽约 1°；收势略低头后回正。整体再乘该段 CameraGain。
     */
    inline constexpr float DiagYaw[CameraSamples]={0.00f,-0.36f,-0.84f,-1.32f,-1.67f,-1.84f,-1.77f,-1.31f,-0.38f,0.78f,1.24f,0.67f,-0.18f,-0.73f,-0.46f,-0.28f,-0.80f,-1.14f,-1.11f,-0.93f,-0.70f,-0.44f,-0.20f,-0.03f,0.11f,0.24f,0.35f,0.41f,0.44f,0.43f,0.36f,0.28f,0.30f,0.39f,0.48f,0.52f,0.41f,0.18f,0.00f};
    inline constexpr float DiagPitch[CameraSamples]={0.00f,0.30f,0.65f,1.01f,1.26f,1.35f,1.29f,1.16f,1.05f,0.80f,0.88f,1.75f,2.11f,1.82f,1.86f,1.69f,1.33f,1.17f,0.87f,0.38f,-0.02f,-0.36f,-0.68f,-0.87f,-0.94f,-0.94f,-0.89f,-0.82f,-0.67f,-0.48f,-0.25f,-0.01f,0.15f,0.23f,0.20f,0.05f,-0.04f,-0.00f,0.00f};
    inline constexpr float DiagRoll[CameraSamples]={0.00f,-0.31f,-0.80f,-1.54f,-2.43f,-3.31f,-3.73f,-3.35f,-2.64f,-1.93f,0.69f,1.81f,1.57f,4.43f,3.95f,2.13f,2.55f,1.54f,1.08f,1.00f,0.54f,0.58f,0.40f,0.38f,0.47f,0.22f,0.09f,0.01f,-0.13f,-0.14f,-0.22f,-0.38f,-0.43f,-0.29f,0.26f,1.05f,1.26f,0.68f,0.00f};
    inline constexpr float DiagFov[CameraSamples]={0.00f,0.26f,0.46f,0.46f,0.31f,0.17f,0.25f,0.40f,0.22f,-0.30f,-0.33f,0.53f,1.07f,0.55f,0.14f,0.50f,0.88f,0.94f,0.74f,0.35f,-0.02f,-0.17f,-0.07f,-0.02f,-0.18f,-0.37f,-0.48f,-0.48f,-0.43f,-0.32f,-0.18f,-0.05f,0.05f,0.09f,0.07f,-0.03f,-0.05f,0.02f,0.00f};
    /**
     * 第三段（V12 戳刺）镜头：参考 #5（1:34.77-1:35.97）只取左上远景配准（Reference/track_atk3.py、contact_atk3.py →
     * atk3_camera.json → curve_atk3.py；靶牌重复、玩家前冲约 2 m 造成视差，近处与中景不参与），按第一段曲线的同一换算比例
     * 写成 30 Hz，翻滚用五点平滑去掉命中时的逐帧抖动（确认命中由 HitShake × HitRoll 补回）。蓄力时略左转、低头约 1.4°、
     * 顺时针滚约 3.8°、视场放宽约 5.5°；刺出瞬间抬头约 3.2°、滚约 5.3°、视场放宽到约 11°；准星上停顿时保持约 +6° 视场，
     * 收回时低头约 2.2° 后回正，约 1.17 s 归零。StabPush 为刺出时沿视线前冲（cm），代替参考里约 2 m 的冲刺位移。
     */
    inline constexpr float StabYaw[CameraSamples]={0.00f,-0.23f,-0.43f,-0.66f,-0.93f,-1.08f,-0.97f,-0.58f,-0.22f,-0.36f,-0.88f,-1.19f,-0.76f,-0.11f,-0.05f,-0.09f,-0.12f,-0.52f,-0.95f,-1.06f,-0.99f,-0.68f,-0.30f,-0.20f,-0.17f,-0.07f,-0.01f,0.01f,0.02f,-0.03f,-0.14f,-0.18f,-0.14f,-0.07f,-0.02f,-0.00f,0.00f,0.00f,0.00f};
    inline constexpr float StabPitch[CameraSamples]={0.00f,0.27f,0.08f,-0.47f,-0.98f,-1.21f,-1.30f,-1.42f,-1.28f,-0.43f,1.05f,2.54f,3.19f,2.56f,1.39f,0.83f,0.62f,0.36f,0.04f,-0.68f,-1.43f,-1.93f,-2.22f,-2.01f,-1.55f,-1.15f,-0.85f,-0.67f,-0.52f,-0.27f,0.03f,0.14f,0.08f,0.03f,0.01f,0.00f,0.00f,0.00f,0.00f};
    inline constexpr float StabRoll[CameraSamples]={0.00f,-0.07f,0.03f,0.42f,1.14f,2.05f,2.85f,3.53f,3.78f,3.18f,3.55f,5.26f,4.74f,2.52f,2.24f,2.97f,2.86f,2.10f,1.12f,0.43f,0.07f,-0.17f,-0.25f,-0.38f,-0.52f,-0.54f,-0.48f,-0.37f,-0.30f,-0.37f,-0.44f,-0.35f,-0.19f,-0.07f,-0.02f,-0.00f,0.00f,0.00f,0.00f};
    inline constexpr float StabFov[CameraSamples]={0.00f,-0.13f,0.06f,0.81f,2.02f,3.32f,4.19f,4.76f,5.56f,7.11f,9.57f,11.09f,10.24f,8.00f,6.18f,5.70f,5.95f,5.66f,4.47f,3.10f,1.80f,0.74f,0.03f,-0.56f,-0.92f,-0.99f,-0.93f,-0.75f,-0.51f,-0.32f,-0.12f,0.07f,0.11f,0.07f,0.02f,0.00f,0.00f,0.00f,0.00f};
    inline constexpr float StabPush[CameraSamples]={0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,2.33f,6.67f,9.00f,9.00f,9.00f,9.00f,8.99f,8.33f,6.85f,4.91f,2.90f,1.18f,0.15f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};
    /**
     * 上挑镜头：参考 #9（106.20-107.30 s）远景配准（Reference/camera_upper.py、curve_upper.py）。蓄力时略右转、低头约 1.3°、
     * 顺时针滚约 1.7°；上撩瞬间左转约 1.9°、抬头到约 4°、视场放宽约 5°、滚到约 5.5°（参考逐帧 +12.6/-2.6° 的命中抖动由 HitShake 补回）；
     * 前臂上举时继续抬头，0.75 s 视场回正、约 1.1 s 全部回正（参考里滑铲带来的位移不计入）。
     */
    inline constexpr float UpperYaw[CameraSamples]={0.00f,0.20f,0.36f,0.45f,0.48f,0.50f,0.51f,0.52f,0.52f,0.15f,-1.43f,-1.87f,-1.56f,-1.12f,-0.90f,-0.71f,-0.57f,-0.45f,-0.35f,-0.26f,-0.18f,-0.11f,-0.05f,-0.01f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};
    inline constexpr float UpperPitch[CameraSamples]={0.00f,-0.28f,-0.53f,-0.74f,-0.92f,-1.10f,-1.24f,-1.29f,-0.93f,0.00f,2.59f,3.49f,4.14f,3.88f,3.31f,2.76f,2.35f,1.96f,1.56f,1.10f,0.40f,-0.38f,-0.74f,-0.71f,-0.64f,-0.55f,-0.45f,-0.37f,-0.29f,-0.21f,-0.13f,-0.07f,-0.02f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};
    inline constexpr float UpperRoll[CameraSamples]={0.00f,0.29f,0.56f,0.80f,0.99f,1.16f,1.31f,1.49f,1.70f,2.00f,5.50f,3.02f,1.70f,1.00f,0.76f,0.59f,0.47f,0.38f,0.30f,0.23f,0.16f,0.09f,0.04f,0.01f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};
    inline constexpr float UpperFov[CameraSamples]={0.00f,0.01f,0.03f,0.07f,0.12f,0.17f,0.23f,0.30f,0.37f,0.52f,3.39f,4.87f,4.10f,2.99f,2.39f,1.88f,1.46f,1.13f,0.84f,0.55f,0.31f,0.12f,0.01f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};
    /**
     * 重击出手镜头：参考 #12（115.60-117.00 s）远景配准（Reference/camera_heavy.py、curve_heavy.py），从蓄满时的镜头
     * （KukriHeavyRhythm::Loaded*）接起。V2 回砍：刀从头后翻过时略抬头（约 3.5°），劈过准星那一下顺时针猛滚到约 +9.5°（参考那一帧
     * +14.5° 的翻滚抖动由命中 HitShake × HitRoll 补回）、视场放宽到约 6°，镜头随刀低头到约 -6.4°（参考 -9..-10 含落地，不计入），
     * 约 0.75 s 回正。
     */
    inline constexpr float HeavyYaw[CameraSamples]={0.22f,0.67f,0.01f,-1.20f,-1.63f,-1.80f,-1.73f,-1.54f,-1.30f,-1.06f,-0.89f,-0.76f,-0.63f,-0.52f,-0.42f,-0.33f,-0.25f,-0.20f,-0.14f,-0.09f,-0.05f,-0.02f,-0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};
    inline constexpr float HeavyPitch[CameraSamples]={2.30f,3.50f,0.95f,-3.68f,-5.46f,-6.25f,-6.39f,-6.44f,-6.18f,-5.59f,-4.90f,-4.32f,-3.71f,-3.09f,-2.51f,-2.02f,-1.62f,-1.24f,-0.91f,-0.65f,-0.46f,-0.29f,-0.14f,-0.04f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};
    inline constexpr float HeavyRoll[CameraSamples]={-4.50f,-2.97f,9.50f,6.50f,2.47f,0.10f,-1.00f,-0.95f,-0.84f,-0.69f,-0.56f,-0.45f,-0.34f,-0.23f,-0.13f,-0.05f,-0.01f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};
    inline constexpr float HeavyFov[CameraSamples]={-1.50f,0.02f,4.10f,6.00f,5.73f,5.25f,4.81f,4.33f,3.84f,3.38f,2.92f,2.45f,2.01f,1.65f,1.37f,1.13f,0.92f,0.73f,0.57f,0.43f,0.32f,0.20f,0.10f,0.03f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};
    /** 整体镜头幅度（1 = 参考原幅）。 */
    inline constexpr float CameraScale=1.f;

    inline float SampleCurve(const float (&Curve)[CameraSamples],float Time)
    {
        const float X=FMath::Clamp(Time*30.f,0.f,float(CameraSamples-1));
        const int32 I=FMath::Min(int32(X),CameraSamples-2);
        return FMath::Lerp(Curve[I],Curve[I+1],X-I);
    }

    /** Swing camera (degrees: pitch/yaw/roll + vertical FOV delta) for one stage at author time T. */
    inline void SwingCamera(int32 Stage,float T,FRotator& Rotation,float& Fov,FVector* Location=nullptr)
    {
        const FSwing& S=Swings[FMath::Clamp(Stage,0,StageCount-1)];
        if(Location)*Location=FVector::ZeroVector;
        // All reference curves are measured from the stance to the stance; the tail fade only guards the last samples.
        const float Gain=CameraScale*S.CameraGain*FMath::Clamp((S.Length-T)/CameraTailSeconds,0.f,1.f);
        if(S.CameraMode==1)
        {
            // The stab: the reference's ~2 m lunge reads as a short push along the view on top of its FOV widening.
            Rotation=FRotator(SampleCurve(StabPitch,T)*S.CameraPitchScale,SampleCurve(StabYaw,T),SampleCurve(StabRoll,T))*Gain;
            Fov=SampleCurve(StabFov,T)*Gain;
            if(Location)*Location=FVector(SampleCurve(StabPush,T)*Gain,0.f,0.f);
            return;
        }
        if(S.CameraMode==4)
        {
            Rotation=FRotator(SampleCurve(HeavyPitch,T)*S.CameraPitchScale,SampleCurve(HeavyYaw,T),SampleCurve(HeavyRoll,T))*Gain;
            Fov=SampleCurve(HeavyFov,T)*Gain;
            return;
        }
        if(S.CameraMode==3)
        {
            Rotation=FRotator(SampleCurve(UpperPitch,T)*S.CameraPitchScale,SampleCurve(UpperYaw,T),SampleCurve(UpperRoll,T))*Gain;
            Fov=SampleCurve(UpperFov,T)*Gain;
            return;
        }
        const bool bDiag=S.CameraMode==2;
        Rotation=FRotator(SampleCurve(bDiag?DiagPitch:CameraPitch,T)*S.CameraPitchScale,
            SampleCurve(bDiag?DiagYaw:CameraYaw,T),SampleCurve(bDiag?DiagRoll:CameraRoll,T))*Gain;
        Fov=SampleCurve(bDiag?DiagFov:CameraFov,T)*Gain;
    }

    /** 命中附加抖动：快速起振、单次回弹后衰减的阻尼振荡（真实秒）。 */
    inline float HitShake(float Age)
    {
        if(Age<0.f||Age>.35f)return 0.f;
        return FMath::Exp(-Age*13.f)*FMath::Sin(Age*2.f*PI*17.f);
    }

    inline float ImpactEnvelope(float Age)
    {
        if(Age<0.f)return 0.f;
        if(Age<.05f)return FMath::InterpEaseOut(0.f,1.f,Age/.05f,2.f);
        return FMath::Exp(-(Age-.05f)*14.f);
    }
}
