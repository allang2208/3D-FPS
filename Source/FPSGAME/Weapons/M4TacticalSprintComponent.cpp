#include "M4TacticalSprintComponent.h"
#include "FPSGunplayAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "ASH12WeaponAssets.h"
#include "M16WeaponAssets.h"
#include "M16Attachments.h"
#include "A762WeaponAssets.h"
#include "A762Attachments.h"
#include "../FPSGAMECharacter.h"

UM4TacticalSprintComponent::UM4TacticalSprintComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UM4TacticalSprintComponent::Configure(ERifleSprintWeapon Weapon)
{
    Reset();
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    const bool bA762=Character && Character->ActiveInventoryWeaponDefinition==A762WeaponAssets::Definition;
    const bool bHadA762=!Clips.IsEmpty() && Clips[0] && Clips[0]->GetPathName().StartsWith(TEXT("/Game/Weapons/A762/"));
    if (CurrentWeapon != Weapon || bA762!=bHadA762) Clips.Reset();
    CurrentWeapon = Weapon;
    CurrentGrip = EM4SprintGrip::Base;
    bEnabled = Weapon != ERifleSprintWeapon::None;
    if (!bEnabled || !Clips.IsEmpty()) return;
    if (bA762)
    {
        for (const TCHAR* Family:{TEXT("base"),TEXT("base"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")})
            for (const TCHAR* Clip:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})
                Clips.Add(LoadObject<UAnimSequence>(nullptr,*(FCString::Strcmp(Family,TEXT("base"))==0
                    ?A762WeaponAssets::AnimationPath(Clip):A762Attachments::AnimationPath(Family,Clip))));
        return;
    }
    if (Weapon == ERifleSprintWeapon::M16)
    {
        const TCHAR* Families[]={TEXT("base"),TEXT("drum"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")};
        const TCHAR* BaseKinds[]={TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")};
        const TCHAR* Kinds[]={TEXT("SprintEnter"),TEXT("SprintLoop"),TEXT("SprintExit")};
        for (int32 Grip=0; Grip<6; ++Grip)
            for (int32 Kind=0; Kind<3; ++Kind)
                Clips.Add(LoadObject<UAnimSequence>(nullptr,*(Grip==0?M16WeaponAssets::AnimationPath(BaseKinds[Kind]):M16Attachments::AnimationPath(Families[Grip],Kinds[Kind]))));
        return;
    }
    if (Weapon == ERifleSprintWeapon::ASH12)
    {
        for (const TCHAR* Grip : {TEXT("base"), TEXT("base"), TEXT("angled"), TEXT("vertical"), TEXT("canted"), TEXT("prism")})
            for (const TCHAR* Kind : {TEXT("Enter"), TEXT("Loop"), TEXT("Exit")})
                Clips.Add(LoadObject<UAnimSequence>(nullptr, *ASH12WeaponAssets::SprintAnimationPath(Kind, Grip)));
        return;
    }
    const TCHAR* WeaponName = Weapon == ERifleSprintWeapon::AKM ? TEXT("AKM") : TEXT("QBZ191");
    for (const TCHAR* Grip : {TEXT("Base"), TEXT("Drum"), TEXT("Angled"), TEXT("Vertical"), TEXT("Canted"), TEXT("Prism")})
        for (const TCHAR* Kind : {TEXT("Enter"), TEXT("Loop"), TEXT("Exit")})
        {
            // Only M4 has a distinct drum support idle. The other rifles keep
            // their base support grip with a drum, matching their idle layer.
            const TCHAR* RifleGrip = FCString::Strcmp(Grip, TEXT("Drum")) == 0 ? TEXT("Base") : Grip;
            const FString Path = Weapon == ERifleSprintWeapon::M4
                ? FString::Printf(TEXT("/Game/Weapons/M4TacticalSprint20260915/%s/A_M4_TacticalSprint_%s_%s"), Grip, Grip, Kind)
                : FString::Printf(TEXT("/Game/Weapons/RifleTacticalSprint20260915/%s/%s/A_%s_TacticalSprint_%s_%s"),
                    WeaponName, RifleGrip, WeaponName, RifleGrip, Kind);
            Clips.Add(LoadObject<UAnimSequence>(nullptr, *Path));
        }
}

void UM4TacticalSprintComponent::Reset()
{
    Progress = Phase = StrideWeight = 0.f;
    bEntering = false;
}

UAnimSequence* UM4TacticalSprintComponent::Clip(int32 Kind) const
{
    const int32 Index = static_cast<int32>(CurrentGrip) * 3 + Kind;
    return Clips.IsValidIndex(Index) ? Clips[Index].Get() : nullptr;
}

bool UM4TacticalSprintComponent::OwnsPose() const
{
    return bEnabled && Clip(0) && Clip(1) && Clip(2);
}

void UM4TacticalSprintComponent::Advance(float DeltaSeconds, bool bWeaponReady,
    bool bSprintRequested, EM4SprintGrip Grip, float StridePhase, float GroundWeight, bool bWeaponActionExit)
{
    if (CurrentGrip != Grip)
    {
        Reset();
        CurrentGrip = Grip;
    }
    if (!bWeaponReady || !OwnsPose())
    {
        Reset();
        return;
    }
    bEntering = bSprintRequested;
    // Walking gets the complete return. A requested weapon action retains the
    // existing 0.18 s sprint-to-fire contract with a 0.16 s presentation exit.
    const float Duration = !bEntering && bWeaponActionExit ? .16f : Clip(bEntering ? 0 : 2)->GetPlayLength();
    Progress = FMath::Clamp(Progress + (bEntering ? 1.f : -1.f)
        * FMath::Max(0.f, DeltaSeconds) / FMath::Max(Duration, UE_SMALL_NUMBER), 0.f, 1.f);
    Phase = FMath::Fmod(StridePhase, 2.f * PI) / (2.f * PI);
    StrideWeight = FMath::Clamp(GroundWeight, 0.f, 1.f);
}

void UM4TacticalSprintComponent::Apply(UFPSGunplayAnimInstance& Animation) const
{
    if (!OwnsPose()) return;
    // Evaluate one canonical track in both directions. Switching between two
    // separately sampled clips could move the arm when reversing mid-transition.
    Animation.SprintClip = Clip(0);
    Animation.SprintTime = Progress * Animation.SprintClip->GetPlayLength();
    // Start/end at the selected grip, with a short fade to its breathing pose.
    Animation.SprintAlpha = FMath::SmoothStep(0.f, .15f, Progress);
    Animation.SprintLoopClip = Clip(1);
    Animation.SprintLoopTime = Phase * Clip(1)->GetPlayLength();
    // Crossfade once the rifle is mostly raised: mixing a fully upright loop
    // with a low intermediate pose bends the hand away from its rigid grip.
    Animation.SprintLoopAlpha = FMath::SmoothStep(.65f, 1.f, Progress) * StrideWeight;
}
