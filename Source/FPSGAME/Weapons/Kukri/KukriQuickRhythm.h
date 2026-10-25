#pragma once

#include "CoreMinimal.h"

/**
 * 尼泊尔弯刀快速近战（F，刀把砸击）作者时钟，复刻 BV1CeYUeSE7b 89.73-90.97 s（近战动作 #3 刀把）。
 * 作者源：SourceAssets/Kukri20261020/fit_pommel.py → quick_keys.json → author_kukri_quick.py（clip "QuickPommel"，30/30 s）。
 * V2（用户 10-23：左肘扭曲、刀应朝玩家刀把朝外、加快、加强打击力度）：参考 1.267 s 按 TIME_MAP 压到 1.0 s。
 *  0.00-0.30 左拳从左下上来，手背朝上直拳打进中间（肘在左缘外），随后张手向左上甩出画；右拳带刀向右出画、在画外上举；
 *  0.30-0.367 右拳从右上方砸下，越来越快，刀身朝后上方指向玩家，刀把朝前领先；11/30 s 刀把命中（参考 0.433 s，下砸终点）；
 *  0.367-0.433 拳从目标上弹回右上；0.433-0.60 停住；0.60-0.70 拳落向右下、刀翻过去指向前方；之后由下抬回架势。
 * 快速近战沿用剑的技能合同：QuickCombatStats 伤害/射程/击退/削韧/流血，CommitQuickCombatCast 一次性扣体力并占用 F，
 * 接触时刻从刀把端沿瞄准方向一次确定性查询（钝器形式），挥空也给镜头冲击；武技独立动作时钟（只受迅捷影响）。
 * 镜头为参考背景配准（Reference/camera_pommel.py → curve_pommel.py，按同一 TIME_MAP 重采样），换算到本作 75° 垂直视场：
 * 左拳出、右臂蓄力时抬头约 +4°、顺时针滚约 +4°；砸下命中时一帧内低头约 3° 并左转约 1.9°；之后视场放宽约 3.7°，0.7 s 轻微低头后回正。
 */
namespace KukriQuickRhythm
{
    inline const TCHAR* Clip=TEXT("QuickPommel");
    inline constexpr float Seconds=30.f/30.f;
    /** 风声在下砸起势（物品 swing_sound 降调），刀把在 11/30 s 命中（参考下砸终点 0.433 s，参考镜头冲击从这一帧开始）。 */
    inline constexpr float SwingSound=.29f, ContactAt=11.f/30.f;
    inline constexpr float SwingVolume=.7f, SwingPitch=.9f;
    /** 刀把在握点坐标里的位置（cm，SM_Kukri：原点=拳心，+Z 刀身；与 kukri_rig.POMMEL 同值）。 */
    inline const FVector Pommel(0.4f,0.f,-12.5f);
    /**
     * 打击（V2 加强）：确认命中顿帧 0.075×1.3 ≈ 0.1 s，挥空也硬停 MissStop；HitShake 冲击 ×1.7、翻滚 ×2（参考命中帧的逐帧翻滚
     * +6.6/-8.8° 在曲线里已平滑，由这里补回）；命中视场冲击一拍（HitFov）；低频闷响叠一层降调的肉击声。
     * 接触瞬间（命中或挥空）真实时间的镜头重音：低头点一下、沿视线前推、视场放宽（Accent*），
     * 再叠快速近战共用判定帧强震 QuickCombatImpactShake 的 ImpulseScale 倍（其他武器为 1 倍，默认镜头倍率下俯仰约 -11.7°）。
     */
    inline constexpr float HitStopScale=1.3f, MissStop=.03f, ImpactScale=1.7f, HitRoll=2.f, HitFov=1.f, MissKick=.6f, ThudPitchScale=.9f;
    inline constexpr float AccentPitch=-1.4f, AccentPushCM=2.5f, AccentFov=1.2f, ImpulseScale=.35f;
    /** 视模冲击：刀把朝前下砸进，接触把手臂推回右上（+yaw 右、+pitch 上）。 */
    inline constexpr float KickYaw=1.f, KickPitch=1.f;

    /** 整体镜头幅度（1 = 参考原幅）。 */
    inline constexpr float CameraScale=1.f;
    inline constexpr int32 QuickSamples=31;
    inline constexpr float QuickYaw[QuickSamples]={0.00f,-0.01f,0.06f,0.43f,0.56f,0.66f,1.02f,1.03f,1.01f,0.92f,0.83f,-0.57f,-1.62f,-1.90f,-1.54f,-1.08f,-0.62f,-0.15f,-0.22f,-0.47f,-0.04f,0.41f,0.82f,0.54f,-0.06f,-0.00f,0.28f,0.43f,0.41f,0.18f,0.00f};
    inline constexpr float QuickPitch[QuickSamples]={0.00f,-0.03f,-0.05f,0.24f,0.66f,1.38f,1.67f,2.25f,2.83f,3.24f,3.45f,3.95f,1.88f,0.87f,1.14f,1.56f,1.51f,0.67f,-0.05f,-0.23f,-0.98f,-1.50f,-1.46f,-1.17f,-0.76f,-0.49f,-0.38f,-0.20f,-0.08f,-0.07f,0.00f};
    inline constexpr float QuickRoll[QuickSamples]={0.00f,0.01f,-0.19f,-0.91f,-1.38f,-1.52f,-0.68f,0.80f,2.40f,3.69f,4.05f,2.94f,0.72f,0.13f,0.81f,1.27f,0.70f,0.11f,0.57f,-0.50f,0.07f,-0.30f,-0.19f,-0.26f,-0.02f,-0.30f,-0.73f,-0.70f,-0.29f,0.20f,0.00f};
    inline constexpr float QuickFov[QuickSamples]={0.00f,-0.01f,-0.02f,0.00f,-0.27f,-0.48f,0.23f,0.26f,0.18f,0.04f,-0.14f,0.69f,1.91f,2.91f,3.43f,3.70f,3.68f,3.55f,2.36f,0.47f,-0.07f,0.01f,-0.08f,-0.72f,-1.35f,-0.99f,0.07f,0.48f,0.28f,0.04f,0.00f};

    inline float Sample(const float (&Curve)[QuickSamples],float Time)
    {
        const float X=FMath::Clamp(Time*30.f,0.f,float(QuickSamples-1));
        const int32 I=FMath::Min(int32(X),QuickSamples-2);
        return FMath::Lerp(Curve[I],Curve[I+1],X-I);
    }

    /** Quick-melee camera (degrees: pitch/yaw/roll + vertical FOV delta) at author time T; Yaw + right, Pitch + up, Roll + clockwise. */
    inline void Camera(float T,FRotator& Rotation,float& Fov)
    {
        Rotation=FRotator(Sample(QuickPitch,T),Sample(QuickYaw,T),Sample(QuickRoll,T))*CameraScale;
        Fov=Sample(QuickFov,T)*CameraScale;
    }
}
