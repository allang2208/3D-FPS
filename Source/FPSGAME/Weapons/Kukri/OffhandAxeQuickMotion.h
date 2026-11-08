#pragma once

#include "HatchetChopRhythm.h"
#include "HatchetDualChopRhythm.h"
#include "HatchetPairRhythm.h"
#include "KukriArmsMeshComponent.h"
#include "KukriOffhandDraw.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"

namespace OffhandAxeQuickMotion
{
    // Retain the quick attack's duration. All events sample the clock of the
    // existing KH sequence (knife on the right, hatchet on the left).
    inline constexpr float Length = HatchetChopRhythm::Swing.Length;
    inline constexpr float ClipRate = HatchetPairRhythm::Attack3Seconds / Length;
    inline constexpr float SwingAt = HatchetDualChopRhythm::SwingSound / ClipRate;
    inline constexpr float ContactAt = HatchetDualChopRhythm::Strike.At / ClipRate;
    inline constexpr float ReleaseAt = KukriRhythm::DualThrustContactEnd / ClipRate;
    // Finish the crossed carry inside the action, then give the gun its own
    // short return. Neither hand starts a second recovery after the cast ends.
    inline constexpr float CarryStart=.48f,CarryEnd=1.08f;
    inline constexpr float Entry=.16f,EntryLead=.04f;
    inline float Ease(float A,float B,float T)
    {const float X=FMath::Clamp((T-A)/(B-A),0.f,1.f);return X*X*X*(X*(X*6.f-15.f)+10.f);}
    inline float Carry(float T){return Ease(CarryStart,CarryEnd,T);}
    inline constexpr float RiftStart=HatchetDualChopRhythm::Rift.Start/ClipRate;
    inline constexpr float RiftEnd=HatchetDualChopRhythm::Rift.End/ClipRate;
    inline const FName RiftTag(TEXT("OffhandHatchetQuickRift"));
    inline const FVector StaffOffset(2.f,-4.f,-1.f);
    inline const TCHAR* IdlePath = TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualIdle.A_Kukri_DualIdle");

    inline void Sample(UKukriArmsMeshComponent& Arms, UAnimSequence* Clip, float Seconds)
    {
        auto* Player = Arms.GetSingleNodeInstance();
        if (!Player || Player->GetCurrentAsset() != Clip)
        {
            Arms.PlayAnimation(Clip, false);
            Arms.SetPlayRate(0.f);
        }
        Arms.SetPosition(FMath::Clamp(Seconds, 0.f, Clip->GetPlayLength()), false);
        Arms.TickAnimation(0.f, false);
        Arms.RefreshBoneTransforms();
    }

    inline FTransform BladeWorld(const UKukriArmsMeshComponent& Arms)
    {
        return KukriOffhandDraw::Grip() * Arms.GetSocketTransform(TEXT("hand_l"));
    }
}
