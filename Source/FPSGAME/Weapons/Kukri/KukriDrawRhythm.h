#pragma once

#include "CoreMinimal.h"

/**
 * 尼泊尔弯刀拔刀 V2（抛刀接住，2026-10-22）作者时钟，复刻 BV1CeYUeSE7b 52.13-52.93 s（切刀 #5 抛刀）。
 * 作者源：SourceAssets/Kukri20261020/fit_equip.py → equip_keys.json → author_kukri_equip.py（clip "Equip"，0.80 s）。
 *  0.00-0.08 右手在画面下方把刀向上一弹（0.083 s 脱手）；0.13-0.23 刀柄朝上、刀身下垂，从画面右下贴着镜头升起；
 *  0.23-0.43 刀在右上方逆时针翻转（空中共转约 290°），张开的右手掌心朝镜头从右下抬起等刀；13/30 s 刀柄落进掌心，0.47 s 握紧，
 *  0.53 s 刀身转成刃口朝镜头、拳落向右下，0.60-0.80 s 回到架势。
 * 刀在脱手到接住之间不在拳里：WPN_root 播放作者的飞行轨迹，UKukriArmsMeshComponent 的握持锁随作者偏离量淡出（≤0.6 cm 锁死、≥2.5 cm 放开）。
 * 镜头为参考背景配准（Reference/camera_equip.py → curve_equip.py），换算到本作 75° 垂直视场（屏幕等效，倍率 1），60 Hz：
 * 切入时滚转 +1.7° 的冲击、抛起时随刀抬头约 1.5°、接住后下沉约 1.3°（含 -0.6° 滚转、视场收窄 0.55°）。
 */
namespace KukriDrawRhythm
{
    inline constexpr float Seconds=24.f/30.f;
    inline constexpr float Release=10.f/120.f;
    inline constexpr float Catch=13.f/30.f;

    /** 脱手时的翻转风声与接住时的拍握声（作者秒）；音量与音高未试听，按需调整。 */
    inline const TCHAR* TossSound=TEXT("/Game/FreeGameSoundsVol1/SFX/Sword_Swing_Fast_Light/Sword_Swing_Fast_Light_01.Sword_Swing_Fast_Light_01");
    inline const TCHAR* CatchSound=TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick");
    inline constexpr float TossAt=Release, TossVolume=.42f, TossPitch=1.12f;
    inline constexpr float CatchAt=Catch, CatchVolume=.22f, CatchPitch=1.35f;
    /** 双持拔刀（clip "DualEquip"）：左手晚 KukriDualEquipBlade::LeftDelay 抛接，同样两声，音量与音高按此倍率略降以区分两只手。 */
    inline constexpr float OffhandVolume=.85f, OffhandPitch=.94f;

    /** 整体镜头幅度（1 = 参考原幅）。 */
    inline constexpr float CameraScale=1.f;
    inline constexpr int32 DrawSamples=49;
    inline constexpr float DrawYaw[DrawSamples]={0.00f,0.35f,0.10f,0.06f,0.02f,0.03f,0.04f,0.01f,-0.01f,-0.00f,0.00f,-0.01f,-0.02f,-0.02f,-0.02f,-0.00f,0.01f,0.00f,-0.01f,0.00f,0.01f,0.02f,0.03f,0.06f,0.08f,0.10f,0.12f,0.12f,0.12f,0.11f,0.10f,0.02f,-0.06f,-0.04f,-0.02f,-0.02f,-0.02f,-0.03f,-0.04f,-0.03f,-0.02f,-0.02f,-0.02f,-0.01f,-0.00f,-0.00f,-0.00f,-0.00f,0.00f};
    inline constexpr float DrawPitch[DrawSamples]={0.00f,0.48f,0.11f,0.06f,0.01f,0.01f,0.01f,0.20f,0.40f,0.51f,0.63f,0.81f,1.00f,1.17f,1.35f,1.44f,1.53f,1.52f,1.52f,1.43f,1.34f,1.25f,1.16f,1.00f,0.84f,0.60f,0.36f,0.14f,-0.07f,-0.34f,-0.60f,-0.93f,-1.25f,-1.20f,-1.15f,-1.05f,-0.94f,-0.80f,-0.66f,-0.52f,-0.39f,-0.31f,-0.24f,-0.12f,-0.03f,-0.01f,0.00f,-0.00f,0.00f};
    inline constexpr float DrawRoll[DrawSamples]={0.00f,1.67f,0.91f,0.53f,0.15f,0.08f,0.01f,0.01f,0.02f,-0.01f,-0.04f,-0.03f,-0.01f,-0.02f,-0.02f,-0.05f,-0.08f,-0.06f,-0.03f,-0.04f,-0.06f,-0.08f,-0.10f,-0.14f,-0.17f,-0.24f,-0.31f,-0.33f,-0.36f,-0.45f,-0.55f,-0.60f,-0.66f,-0.56f,-0.46f,-0.28f,-0.10f,-0.04f,0.01f,-0.00f,-0.01f,0.00f,0.01f,-0.00f,-0.01f,-0.01f,-0.00f,0.00f,0.00f};
    inline constexpr float DrawFov[DrawSamples]={0.00f,0.04f,-0.07f,-0.08f,-0.08f,-0.05f,-0.01f,0.06f,0.14f,0.21f,0.29f,0.35f,0.41f,0.43f,0.45f,0.45f,0.45f,0.46f,0.47f,0.45f,0.42f,0.36f,0.31f,0.22f,0.14f,0.02f,-0.10f,-0.19f,-0.28f,-0.34f,-0.41f,-0.48f,-0.55f,-0.53f,-0.51f,-0.44f,-0.37f,-0.34f,-0.32f,-0.29f,-0.26f,-0.20f,-0.14f,-0.08f,-0.03f,-0.01f,-0.00f,0.00f,0.00f};

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
