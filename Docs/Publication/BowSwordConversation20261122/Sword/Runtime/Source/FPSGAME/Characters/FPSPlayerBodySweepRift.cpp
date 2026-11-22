#include "FPSPlayerBodyComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyPoses.h"
#include "FPSBodyHighlandMotion.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/BeiweiSwordTrailComponent.h"
#include "../Weapons/HighlandBreakSweep.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

void UFPSPlayerBodyComponent::PresentSwordSweepRift()
{
    if(GetNetMode()==NM_DedicatedServer||!BodyAnimation||!Character.IsValid())return;
    const auto& State=BodyAnimation->BodyState;
    UStaticMeshComponent* Blade=nullptr;
    if((!Character->IsLocallyControlled()||IsThirdPersonViewEnabled())&&State.Family==TEXT("Melee")&&
        State.bHasActionProgress&&FPSBodyHighlandMotion::IsSweep(State.ActionVariant)&&
        !FPSBodyPoses::Traversing(State.Motion)&&!IsWorldBodyPresentationHidden())
    {
        for(const auto& Binding:MotionBindings)
        {
            const auto& Weapon=Binding.Definition;
            if(Weapon.ItemInstance!=State.WeaponInstance||Weapon.PoseFamily!=TEXT("Sword"))continue;
            const int32 Index=Weapon.Parts.IndexOfByPredicate([](const auto& Part){return Part.Slot==TEXT("blade_1");});
            if(Binding.Parts.IsValidIndex(Index))Blade=Binding.Parts[Index].Get();
            break;
        }
    }
    if(!Blade||!Blade->GetStaticMesh()||!Blade->IsVisible()||Blade->bHiddenInGame||IsWorldWeaponStowed(Blade))
    {
        if(PreviousSweepBlade.IsValid()&&WorldSweepTrail)WorldSweepTrail->Clear();
        PreviousSweepBlade.Reset();
        return;
    }
    if(!WorldSweepTrail)
    {
        WorldSweepTrail=NewObject<UBeiweiSwordTrailComponent>(GetOwner());
        WorldSweepTrail->ConfigureSingleMaterial(FSoftObjectPath(TEXT("/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift.M_RuneRift")),.14f);
        GetOwner()->AddInstanceComponent(WorldSweepTrail);
        WorldSweepTrail->RegisterComponent();
    }
    const double Now=GetWorld()->GetTimeSeconds();
    const float Progress=FPSBodyPoses::Progress(State,BodyAnimation->Clock);
    const FTransform Pose=Blade->GetComponentTransform();
    const bool SameBlade=PreviousSweepBlade.Get()==Blade&&Now-PreviousSweepTime<=.25;
    const bool Continuous=SameBlade&&PreviousSweepVariant==State.ActionVariant&&Progress>=PreviousSweepProgress;
    if(!Continuous)WorldSweepTrail->Clear();
    if(State.Action==EFPSBodyAction::Strike||State.Action==EFPSBodyAction::HeavyStrike)
    {
        // Clip the interval between the two finalized world poses to the actual strike.
        // A short contact can fall entirely between two observer frames.
        float From=PreviousSweepProgress;
        if(!Continuous)
        {
            // The charge animation ends at the chamber key in the release take. A
            // delayed first release packet can already be past the complete contact arc.
            if(PreviousSweepVariant==RingChainSweepMotion::Charge&&State.ActionVariant==RingChainSweepMotion::Release)
                From=PreviousSweepProgress*State.ContactFraction*(RingChainSweepMotion::Chamber/HighlandBreakSweep::Contact);
            else
                From=FMath::Max(0.f,Progress-float(Now-PreviousSweepTime)/FMath::Max(.001f,State.ActionDuration));
        }
        const float Start=FMath::Max(From,State.ContactFraction),End=FMath::Min(Progress,State.ReleaseFraction);
        if(SameBlade&&End>Start&&Progress>From)
        {
            const FBox Bounds=Blade->GetStaticMesh()->GetBoundingBox();
            for(const float P:{Start,End})
            {
                const float Alpha=(P-From)/(Progress-From);
                FTransform Sample;Sample.Blend(PreviousSweepPose,Pose,Alpha);
                WorldSweepTrail->Feed(Sample.TransformPosition(FVector(0,0,Bounds.Min.Z)),
                    Sample.TransformPosition(FVector(0,0,Bounds.Max.Z)),true,ESwordTrailPalette::Gold,(1.-Alpha)*(Now-PreviousSweepTime));
            }
        }
    }
    PreviousSweepBlade=Blade;PreviousSweepVariant=State.ActionVariant;
    PreviousSweepPose=Pose;PreviousSweepProgress=Progress;PreviousSweepTime=Now;
}
