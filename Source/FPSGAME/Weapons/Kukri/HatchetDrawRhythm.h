#pragma once

#include "CoreMinimal.h"

/**
 * 碳钢战斧拔斧 V2.1（参考 BV1pqkyYyEDY 38.70-39.55 s「切刀动作 #2 抛」，2026-11-02）作者时钟。
 * 作者源：SourceAssets/HatchetEquip20261101/author_hatchet_equip.py（clip "HatchetEquip"，0.900 s；本文件由该脚本 --header 生成）。
 *  0-0.15 拳握斧柄上段，把斧子从画面下方提起、斧头先露出，到位时手腕把斧头向后扣；随即翻起，0.183 s 松手；
 *  斧子在空中不旋转地上浮、摆正并向右靠近，张开的右手先让到右侧再下探斧柄下段，0.383 s 握住；
 *  随后下拉并前送到画面中央，斧头先右倾再左倾、刃口转向前方，0.85 s 收进与弯刀共用的持斧架势。
 * 斧子离手和握在柄上段期间 WPN_root 播放作者轨迹，UKukriArmsMeshComponent 的握持锁随作者偏离量淡出（≤0.6 cm 锁死、≥2.5 cm 放开）。
 * 镜头为参考背景配准（Reference/camera_ref.py），换算到本作 75° 垂直视场，60 Hz：抛起时随斧抬头约 2.4°、右转约 2°，
 * 前送时下沉回摆，0.72 s 后淡出回正。
 */
namespace HatchetDrawRhythm
{
    inline const TCHAR* Clip=TEXT("/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_Equip.A_TacticalHatchet_Equip");
    inline constexpr float Seconds=0.9000f;
    inline constexpr float Release=0.1833f;
    inline constexpr float Catch=0.3833f;

    /** 翻斧脱手的风声与接柄握声（作者秒，沿用弯刀拔刀的两条资产）；音量与音高未试听，按需调整。 */
    inline constexpr float TossAt=Release, TossVolume=0.36f, TossPitch=0.95f;
    inline constexpr float CatchAt=Catch, CatchVolume=0.32f, CatchPitch=1.05f;

    /** 整体镜头幅度（1 = 参考原幅）。 */
    inline constexpr float CameraScale=1.f;
    inline constexpr int32 DrawSamples=55;
    inline constexpr float DrawPitch[DrawSamples]={0.00f,0.04f,0.08f,0.11f,0.21f,0.32f,0.42f,0.56f,0.70f,0.85f,1.04f,1.24f,1.39f,1.54f,1.68f,1.81f,1.92f,2.03f,2.14f,2.25f,2.30f,2.36f,2.40f,2.43f,2.43f,2.43f,2.33f,2.24f,1.97f,1.70f,1.22f,0.74f,0.32f,-0.09f,-0.31f,-0.52f,-0.49f,-0.46f,-0.36f,-0.25f,-0.13f,0.00f,0.13f,0.26f,0.39f,0.49f,0.52f,0.50f,0.42f,0.32f,0.20f,0.10f,0.04f,0.01f,0.00f};
    inline constexpr float DrawYaw[DrawSamples]={0.00f,0.06f,0.12f,0.18f,0.26f,0.34f,0.42f,0.47f,0.52f,0.58f,0.64f,0.70f,0.75f,0.80f,0.88f,0.96f,1.04f,1.13f,1.23f,1.34f,1.43f,1.53f,1.61f,1.70f,1.78f,1.85f,1.87f,1.89f,1.79f,1.69f,1.41f,1.13f,0.78f,0.43f,0.17f,-0.10f,-0.21f,-0.32f,-0.33f,-0.34f,-0.30f,-0.25f,-0.16f,-0.07f,0.02f,0.11f,0.14f,0.15f,0.12f,0.08f,0.05f,0.02f,0.01f,0.00f,0.00f};
    inline constexpr float DrawRoll[DrawSamples]={0.00f,0.01f,0.01f,0.02f,0.03f,0.04f,0.05f,0.11f,0.17f,0.23f,0.29f,0.35f,0.44f,0.53f,0.58f,0.63f,0.67f,0.70f,0.70f,0.70f,0.73f,0.76f,0.80f,0.84f,0.88f,0.92f,0.85f,0.79f,0.63f,0.46f,0.21f,-0.05f,-0.21f,-0.37f,-0.42f,-0.46f,-0.40f,-0.35f,-0.29f,-0.24f,-0.18f,-0.12f,-0.08f,-0.04f,0.00f,0.03f,0.05f,0.06f,0.05f,0.03f,0.02f,0.01f,0.00f,0.00f,0.00f};
    inline constexpr float DrawFov[DrawSamples]={0.00f,-0.01f,-0.03f,-0.04f,-0.05f,-0.06f,-0.07f,-0.10f,-0.13f,-0.16f,-0.16f,-0.15f,-0.16f,-0.17f,-0.17f,-0.18f,-0.12f,-0.06f,-0.05f,-0.03f,0.03f,0.10f,0.12f,0.14f,0.20f,0.25f,0.23f,0.22f,0.14f,0.06f,-0.04f,-0.15f,-0.17f,-0.19f,-0.18f,-0.17f,-0.10f,-0.03f,-0.01f,0.02f,0.02f,0.02f,0.01f,0.00f,-0.02f,-0.03f,-0.03f,-0.02f,-0.01f,-0.01f,0.00f,0.00f,0.00f,0.00f,0.00f};

    inline float SampleDraw(const float (&Curve)[DrawSamples],float Time)
    {
        const float X=FMath::Clamp(Time*60.f,0.f,float(DrawSamples-1));
        const int32 I=FMath::Min(int32(X),DrawSamples-2);
        return FMath::Lerp(Curve[I],Curve[I+1],X-I);
    }

    /** Draw camera (degrees: pitch/yaw/roll + vertical FOV delta) at author time T; Yaw + right, Pitch + up, Roll + clockwise. */
    inline void Camera(float T,FRotator& Rotation,float& Fov)
    {
        Rotation=FRotator(SampleDraw(DrawPitch,T),SampleDraw(DrawYaw,T),SampleDraw(DrawRoll,T))*CameraScale;
        Fov=SampleDraw(DrawFov,T)*CameraScale;
    }
}
