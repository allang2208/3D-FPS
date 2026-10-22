#pragma once

#include "CoreMinimal.h"
#include "../../Combat/MonsterToughnessTypes.h"

/**
 * 尼泊尔弯刀（Kukri）作者动作时钟。所有数值都是作者秒（120 fps 源、30 fps 重采样网格），
 * 运行时统一乘以同一个播放速率；命中窗、挥空声、镜头曲线与顿帧共用这一条时钟。
 *
 * 2026-10-20 V2：三连击暂停，只保留一段攻击——逐帧复刻 BV1CeYUeSE7b 1:27.00-1:28.27
 * （近战 #2 从右到左大范围横挥）。作者源：SourceAssets/Kukri20261020/fit_reference.py →
 * attack_keys.json → author_kukri_clips.py（clip "Attack"）。
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
     * 两段连击（2026-10-20 第二段）：
     *  第一段 Attack（右→左，上述相位）：0.20 s 起的点击缓冲一次，到 17/30 s（前臂横在左下、刚扫完）直接接第二段；
     *    无点击则播完 1.267 s 回待机。
     *  第二段 Attack2（V7 左上→右下斜劈，1.0 s）：从第一段 17/30 s 的姿态起手，0.00-0.17 拳心在身前抬到左上蓄势
     *    （拳心深 ≥ 27 cm、刀尖在拳前，不朝头部），0.17-0.30 以与第一段相同的屏幕速度斜劈过画面中心
     *    （刃口沿劈砍方向领先，命中 0.19-0.31），0.30-0.47 从右下角出画，0.47-1.00 抬回待机。
     *    0.15 s 起的点击缓冲一次，在 0.40 s（拳刚从右下出画）直接接第三段；无点击则播完回待机。
     *  第三段 Attack3（V8 双手前刺，1.1 s）：从第二段 0.40 s 的姿态起手，0.07-0.17 左手掌心抵上刀柄尾端，
     *    0.17-0.20 双手收到胸前（拳心深约 20 cm、刀尖指向画面中心），0.20-0.30 沿视线向前刺出到约 46 cm，
     *    命中 0.26-0.38 并稍作停顿，0.45-0.58 左手松开落下，右手回到待机。0.55 s 起的点击缓冲一次，播完后从待机接回第一段。
     * 三段同伤害、同播放速率（物品攻速）。第二段镜头 = 第一段曲线提前 0.133 s 并左右镜像（偏航、翻滚取反），
     * 俯仰取反按 0.7 倍（蓄势时略抬头、劈下后低头跟随）；第三段用程序化前刺镜头（蓄力略后仰收窄、刺出时前冲低头放宽）。
     * 接段时用 0.18 s 把上一段残余镜头偏移平滑并入。副手持枪／魔法书时左臂收起，第三段为单手前刺。
     */
    struct FSwing
    {
        const TCHAR* Clip;
        float Length,SwingSound,ContactStart,ContactEnd;
        float BufferOpen;   // earliest author time a click is buffered
        float ChainAt;      // author time the buffered follow-up takes over (Length = after the swing)
        float CameraShift;  // sample the reference camera curve at (t + shift)
        float Mirror;       // +1 reference direction (right->left), -1 mirrored (left->right)
        float SwingPitch;
        float CameraPitchScale; // V6: the reference's post-cut look-up read as "stabbing up-left"; keep the sweep level.
                                // V7 diagonal: negative = inverted (look up in the cock, follow the cut down).
        int32 CameraMode;       // 0 = reference swing curve, 1 = procedural thrust
        float HitStopScale;     // flesh hit-stop multiplier (V9: the thrust lands heavier)
        float ImpactScale;      // hit shake / FOV punch multiplier
    };
    inline constexpr int32 SwingCount=3;
    inline constexpr FSwing Swings[SwingCount]={
        {TEXT("Attack"), 38.f/30.f,.27f,.32f,.45f,.20f,17.f/30.f,0.f,   1.f,.96f,.4f, 0,1.f, 1.f},
        {TEXT("Attack2"),30.f/30.f,.17f,.19f,.31f,.15f,.40f,     .1333f,-1.f,1.04f,-.7f,0,1.f, 1.f},
        {TEXT("Attack3"),33.f/30.f,.22f,.26f,.38f,.55f,33.f/30.f,0.f,   1.f,1.10f,1.f, 1,1.6f,1.25f},
    };

    /**
     * 速度（用户：快得几乎看不清）：V9 慢 25%，V10 再慢 25%——物品 attack_seconds = clip 作者长度 × 1.5625，
     * 三段基础播放速率 0.64（第一段 1.98 s、第二段 1.56 s）。
     * 第三段前刺再叠一层分相变速，制造顿挫：接近 0.85 倍 → 蓄力收肘 0.17-0.215 停顿 0.40 倍 →
     * 刺出 0.215-0.30 加快到 1.15 倍 → 刺到底 0.30-0.40 停顿 0.40 倍 → 收回 0.85 倍。
     * 实际时长（无攻速加成）约 2.28 s（原 1.1 s）；命中顿帧 ×1.6、冲击 ×1.25。
     */
    inline float PhaseRate(int32 Stage,float T,float& SegmentEnd)
    {
        if(Stage!=2)return 1.f;
        struct FSeg{float End,Rate;};
        static constexpr FSeg Segs[]={{.17f,.85f},{.215f,.40f},{.30f,1.15f},{.40f,.40f}};
        for(const FSeg& S:Segs)
            if(T<S.End-UE_KINDA_SMALL_NUMBER){SegmentEnd=FMath::Min(SegmentEnd,S.End);return S.Rate;}
        return .85f;
    }

    /** Procedural thrust camera (author seconds): cock leans back and narrows, the drive lunges forward
     *  (camera +4 cm), dips and widens, held through the extension and released by ~0.85 s. */
    inline void ThrustCamera(float T,FRotator& Rotation,float& Fov,FVector& Location)
    {
        const float Cock=FMath::SmoothStep(.08f,.20f,T)*(1.f-FMath::SmoothStep(.20f,.27f,T));
        const float Drive=FMath::SmoothStep(.20f,.29f,T)*(1.f-FMath::SmoothStep(.42f,.85f,T));
        const float Snap=FMath::SmoothStep(.24f,.30f,T)*(1.f-FMath::SmoothStep(.30f,.46f,T));
        Rotation=FRotator(1.2f*Cock-2.2f*Drive,.6f*Cock-.4f*Drive,1.6f*Snap-.5f*Drive);
        Fov=-1.2f*Cock+4.f*Drive;
        Location=FVector(4.f*Drive,0.f,-.6f*Drive);
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
        const FSwing& S=Swings[FMath::Clamp(Stage,0,SwingCount-1)];
        if(Location)*Location=FVector::ZeroVector;
        if(S.CameraMode==1)
        {
            FVector Lunge;ThrustCamera(T,Rotation,Fov,Lunge);
            Rotation*=CameraScale;Fov*=CameraScale;
            if(Location)*Location=Lunge*CameraScale;
            return;
        }
        const float C=T+S.CameraShift;
        // Mirrored stages end before the reference curve has settled: fade the tail into the stance.
        const float Tail=S.CameraShift>0.f?FMath::Clamp((S.Length-T)/CameraTailSeconds,0.f,1.f):1.f;
        Rotation=FRotator(SampleCurve(CameraPitch,C)*S.CameraPitchScale,SampleCurve(CameraYaw,C)*S.Mirror,SampleCurve(CameraRoll,C)*S.Mirror)*(CameraScale*Tail);
        Fov=SampleCurve(CameraFov,C)*CameraScale*Tail;
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
