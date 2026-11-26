#include "PistolDualWieldComponent.h"
#include "Kukri/KukriWeaponComponent.h"
#include "FPSGunplayAnimInstance.h"
#include "WeaponGripProfile.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/LightningHasteSpeed.h"

namespace
{
constexpr float LowerSeconds=.075f;
float Ease(float U){return U*U*U*(U*(U*6.f-15.f)+10.f);}
}

bool UPistolDualWieldComponent::MainMeleeBusy() const
{
    const auto* Knife=IsMeleePair()&&Player?Player->FindComponentByClass<UKukriWeaponComponent>():nullptr;
    return Knife&&Knife->IsEquipped()&&Knife->IsBusy();
}

bool UPistolDualWieldComponent::IsMeleePairBlocked() const
{
    // Query the action as well as the blend: a click between actor and weapon ticks
    // must not fire on the first frame of the knife's swing.
    return IsMeleePair()&&(MainMeleeBusy()||MeleeAvoidance>UE_KINDA_SMALL_NUMBER);
}

void UPistolDualWieldComponent::QueueMeleeReload(const FString& AmmoType)
{
    if(!IsMeleePair())return;
    Hands[1].PendingAmmoType=AmmoType;Hands[1].ReloadQueued=true;
}

void UPistolDualWieldComponent::RestoreMeleeTrigger(bool Held,bool Pending)
{
    if(!IsMeleePair())return;
    // Retain a pending click, but never turn an already fired semi-auto press
    // into a second shot when F finishes. Button release still clears both.
    Hands[1].Held=Held;Hands[1].Pending=Held&&Pending;
}

void UPistolDualWieldComponent::CaptureMeleeReleasePose(int32 Index)
{
    if(Index!=1||!IsMeleePair())return;
    const auto& Gun=Hands[1];
    if(!Gun.Reloading||!Gun.Anim||!Gun.Anim->ActionClip)return;
    // Keep the last rendered reload frame while lowering. Its gameplay clock
    // and mechanical audio stop immediately; this layer only blends the pose.
    MeleeReleaseClip=Gun.Anim->ActionClip;MeleeReleaseGrip=Gun.Anim->GripProfile;
    MeleeReleaseTime=Gun.Anim->ActionTime;MeleeReleaseAlpha=Gun.Anim->ActionAlpha;MeleeReleaseAge=0.f;
}

void UPistolDualWieldComponent::ApplyMeleeReleasePose(int32 Index)
{
    if(Index!=1||!IsMeleePair()||!MeleeReleaseClip)return;
    auto* Anim=Hands[1].Anim.Get();
    Anim->ActionClip=MeleeReleaseClip;Anim->ActionTime=MeleeReleaseTime;
    Anim->ActionAlpha=MeleeReleaseAlpha*(1.f-Ease(FMath::Clamp(MeleeReleaseAge/LowerSeconds,0.f,1.f)));
    Anim->GripProfile=MeleeReleaseGrip;
}

void UPistolDualWieldComponent::AdvanceMeleePair(float Delta)
{
    if(!IsMeleePair()){MeleeAvoidance=0.f;return;}
    const float ActionDelta=FMath::Max(0.f,Delta)*LightningHaste::ActionSpeed(Player);
    if(MeleeReleaseClip)
    {
        MeleeReleaseAge+=ActionDelta;
        if(MeleeReleaseAge>=LowerSeconds){MeleeReleaseClip=nullptr;MeleeReleaseGrip=nullptr;}
    }
    const bool Busy=MainMeleeBusy();
    auto& Gun=Hands[1];
    if(Busy&&Gun.Reloading)
    {
        // Retain completed insertions/case ejection/cycle-needed state through the
        // existing ammo receipt. Restart only the remaining reload after recovery.
        const FString AmmoType=Gun.PendingAmmoType;
        StopAction(1);QueueMeleeReload(AmmoType);
    }
    const float Seconds=Busy?LowerSeconds:.18f;
    const bool WasAvoiding=MeleeAvoidance>UE_KINDA_SMALL_NUMBER;
    MeleeAvoidance=FMath::FInterpConstantTo(MeleeAvoidance,Busy?1.f:0.f,
        ActionDelta,1.f/Seconds);
    // A queued right-click must not interrupt the blade's sprint attack.
    // Release sprint only when the pistol can actually take over again.
    if(WasAvoiding&&!IsMeleePairBlocked()&&Gun.Held)Player->ExitSprintForWeapon();
}

void UPistolDualWieldComponent::ApplyMeleePairPose(int32 Index,FVector& Offset,FQuat& Rotation) const
{
    if(Index!=1||!IsMeleePair())return;
    const float W=Ease(MeleeAvoidance);
    // Move the complete native left rig: grip, fingers and mechanical bones stay
    // together. The right blade keeps every one of its original single-hand clips.
    Offset+=FVector(-8.f,-22.f,-38.f)*W;
    Rotation=(FRotator(-20.f*W,0.f,18.f*W).Quaternion()*Rotation).GetNormalized();
}
