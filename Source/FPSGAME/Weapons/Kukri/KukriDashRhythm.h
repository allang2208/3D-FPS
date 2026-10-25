#pragma once

#include "CoreMinimal.h"

/**
 * 尼泊尔弯刀冲刺攻击（被动技能 dashAttack）作者时钟：双手跳劈，复刻 BV1CeYUeSE7b 112.47-113.80 s（近战动作（跳跃）#11 跳劈）。
 * 作者源：SourceAssets/Kukri20261020/fit_sprint.py → sprint_keys.json → author_kukri_sprint.py（clip "SprintAttack"，1.333 s）。
 *  0.03-0.07 右拳带刀抬起、刀身转直，左手从左下上来；0.10 双手在画面上方中间合握刀柄；0.13 双臂出画上方；
 *  0.17-0.33 举过头顶蓄势（画外）；0.37 双臂从上方劈下；0.40 拳到画面下方、刀身向前下劈；0.43 命中（参考闪光在准星）；
 *  0.45 左手松开；0.43-1.03 双臂在画外；1.07-1.33 右拳由下抬回架势。
 * 武技独立动作时钟：不随武器攻速缩放，只受迅捷（LightningHaste）影响。
 * 镜头为参考背景配准（Reference/camera_sprint.py → curve_sprint.py），换算到本作 75° 垂直视场：
 * 举刀时随跳起抬头到约 +8.7°，劈下穿过水平线，落地时低头到约 -8.6°，0.55 s 后在 1.1 s 前回正。
 */
namespace KukriDashRhythm
{
    inline constexpr float Seconds=40.f/30.f;
    inline constexpr float SwingSound=.333f;
    /** 命中窗：刀从头顶劈过准星前方区域（作者秒）；窗内按前方扇区查询，每目标一次。 */
    inline constexpr float ContactStart=.367f, ContactEnd=.467f;
    inline constexpr float SwingPitch=.88f;
    /** 确认命中：顿帧、抖动/视场冲击倍率（相对普通挥砍），视模被向上顶回。 */
    inline constexpr float HitStopScale=1.6f, ImpactScale=1.3f, HitRoll=1.2f;
    inline constexpr float KickYaw=0.f, KickPitch=1.f;
    /**
     * 空间扰动（剑气，2026-10-24）：刀从画面上方劈过准星到下方的弧形带（KukriSkillRiftRibbons::Dash，
     * author_kukri_skill_rift.py 的同一窗口），随劈砍作者时钟展开，之后真实时间溶解并向前漂。
     * 强度取双手剑冲刺下劈（.16）与弯刀挥砍（.08）之间，刀短。展开期间跟着角色的冲刺位移走。
     */
    inline constexpr float RiftStart=.345f, RiftEnd=.410f, RiftStrength=.12f, RiftDissolve=.26f, RiftDriftCM=95.f;

    /** 整体镜头幅度（1 = 参考原幅）。 */
    inline constexpr float CameraScale=1.f;
    inline constexpr int32 DashSamples=41;
    inline constexpr float DashYaw[DashSamples]={0.00f,-0.02f,0.01f,0.09f,0.72f,0.77f,1.36f,1.19f,1.14f,1.10f,1.20f,1.28f,-0.13f,0.89f,0.90f,1.63f,1.87f,1.95f,2.65f,2.92f,3.22f,3.39f,3.55f,3.39f,3.16f,2.78f,2.33f,1.86f,1.37f,0.93f,0.53f,0.24f,0.06f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};
    inline constexpr float DashPitch[DashSamples]={0.00f,0.60f,2.25f,4.03f,5.61f,7.13f,8.26f,8.73f,8.66f,7.94f,5.50f,-0.07f,-1.95f,-5.88f,-8.16f,-8.63f,-8.49f,-6.76f,-4.83f,-2.78f,-2.27f,-2.42f,-2.54f,-2.61f,-2.47f,-2.20f,-1.89f,-1.50f,-1.12f,-0.75f,-0.43f,-0.19f,-0.05f,-0.00f,-0.00f,-0.00f,-0.00f,-0.00f,-0.00f,-0.00f,0.00f};
    inline constexpr float DashRoll[DashSamples]={0.00f,-0.25f,-0.58f,-0.72f,-2.22f,-2.48f,-3.53f,-3.28f,-3.18f,-3.02f,-2.88f,-2.24f,-1.66f,-2.42f,-1.84f,-2.59f,-2.89f,-3.46f,-3.61f,-3.28f,-3.20f,-3.67f,-2.04f,-2.58f,-1.96f,-1.57f,-1.50f,-1.03f,-0.81f,-0.55f,-0.31f,-0.15f,-0.04f,-0.00f,-0.00f,-0.00f,-0.00f,-0.00f,-0.00f,-0.00f,0.00f};
    inline constexpr float DashFov[DashSamples]={0.00f,0.11f,0.27f,1.23f,1.19f,1.19f,2.00f,2.24f,2.25f,1.94f,1.34f,-0.56f,1.99f,1.31f,3.21f,3.20f,3.27f,3.85f,4.43f,4.75f,4.61f,4.16f,3.61f,3.07f,2.55f,2.09f,1.67f,1.28f,0.94f,0.63f,0.37f,0.18f,0.05f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f,0.00f};

    inline float Sample(const float (&Curve)[DashSamples],float Time)
    {
        const float X=FMath::Clamp(Time*30.f,0.f,float(DashSamples-1));
        const int32 I=FMath::Min(int32(X),DashSamples-2);
        return FMath::Lerp(Curve[I],Curve[I+1],X-I);
    }

    /** Sprint-attack camera (degrees: pitch/yaw/roll + vertical FOV delta) at author time T; Yaw + right, Pitch + up, Roll + clockwise. */
    inline void Camera(float T,FRotator& Rotation,float& Fov)
    {
        Rotation=FRotator(Sample(DashPitch,T),Sample(DashYaw,T),Sample(DashRoll,T))*CameraScale;
        Fov=Sample(DashFov,T)*CameraScale;
    }
}
