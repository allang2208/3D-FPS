#pragma once
#include "CoreMinimal.h"

/** Inspect V85 presentation: cue times follow SourceAssets/RuneSword20260913/InspectReverseV85/v85_keys.py
 *  (reference #10 绕手 played in reverse; R4 runs the turn on one continuous speed clock). Camera values are
 *  camera-local centimetres/degrees before the sword's shared camera multiplier; the inspect stays a local,
 *  cosmetic action. */
namespace RuneSwordInspectFeel
{
    // R3 (user: R2 too fast/stiff, sounds thin): heavier whooshes, a gauntlet knock when the hanging blade lands
    // in the web, and a layered thud + plate rattle when the fist closes. Pitches below 1 give the weight.
    inline const TCHAR* WhipSoundPath=TEXT("/Game/FreeGameSoundsVol1/SFX/Sword_Swing_Heavy/Sword_Swing_Heavy_01.Sword_Swing_Heavy_01");
    inline const TCHAR* SnapSoundPath=TEXT("/Game/FreeGameSoundsVol1/SFX/Sword_Swing_Overhead/Sword_Swing_Overhead_01.Sword_Swing_Overhead_01");
    inline const TCHAR* GripSoundPath=TEXT("/Game/FreeGameSoundsVol1/SFX/Armor_Plate_Movement/Armor_Plate_Movement_01.Armor_Plate_Movement_01");
    // Cues and camera are written on a motion clock that the clip plays at 1/Tempo (R5 played 0.8x).
    inline constexpr float Tempo=1.f;
    // R6b hybrid on V82's timetable (InspectReverseV85/author_inspect_r6.py cue_clip_s): the fist opens at 0.40 s;
    // the hilt settles on V82's open palm about 0.53 s; the drive home starts about 0.70 s; the fist closes at 0.82 s.
    namespace Motion { inline constexpr float Whip=.414f, Land=.528f, Snap=.701f, Catch=.822f; }
    inline constexpr float WhipCue=Motion::Whip*Tempo, LandCue=Motion::Land*Tempo, SnapCue=Motion::Snap*Tempo,
        CatchAt=Motion::Catch*Tempo;
    inline constexpr float WhipVolume=.55f, WhipPitch=.90f;
    inline constexpr float LandVolume=.22f, LandPitch=.86f;
    inline constexpr float SnapVolume=.60f, SnapPitch=.86f;
    inline constexpr float CatchVolume=.50f, CatchPitch=.74f;
    inline constexpr float CatchRattleVolume=.40f, CatchRattlePitch=.94f;

    /** Weight loads in the windup, a small dip when the blade lands in the web, and one slow damped nod when
     *  the fist takes the sword's weight. */
    inline void Camera(float T,FVector& Location,FRotator& Rotation)
    {
        T/=Tempo;
        const float Windup=FMath::SmoothStep(.26f,.39f,T)*(1.f-FMath::SmoothStep(.40f,.47f,T));
        Rotation.Roll+=.6f*Windup;Location.Y+=.3f*Windup;Location.Z-=.3f*Windup;
        const float Whip=FMath::Clamp((T-Motion::Whip)/.12f,0.f,1.f);
        const float Burst=FMath::Square(FMath::Sin(PI*Whip));
        Rotation.Roll-=.6f*Burst;Rotation.Yaw-=.3f*Burst;
        const float L=T-Motion::Land;
        if(L>=0.f&&L<.20f)
        {
            const float Dip=FMath::Exp(-14.f*L)*FMath::Sin(36.f*L);
            Rotation.Pitch+=.30f*Dip;Location.Z-=.18f*Dip;
        }
        const float A=T-Motion::Catch;
        if(A>=0.f&&A<.42f)
        {
            const float Kick=FMath::Exp(-9.f*A)*FMath::Sin(30.f*A)*(1.f-FMath::SmoothStep(.10f,.42f,A));
            Rotation.Pitch+=1.5f*Kick;Rotation.Roll+=.5f*Kick;
            Location.X-=1.1f*Kick;Location.Z-=.5f*Kick;
        }
    }
}
