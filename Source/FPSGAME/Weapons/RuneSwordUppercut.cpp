#include "RuneSwordComponent.h"
#include "RuneSwordUppercutMotion.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/SkeletalMesh.h"

void URuneSwordComponent::LoadUppercutAnimations()
{
    UppercutLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(
        TArray<FSoftObjectPath>{UppercutStandard.ToSoftObjectPath(),UppercutLongGrip.ToSoftObjectPath()});
}

UAnimSequence* URuneSwordComponent::UppercutAnimation() const
{
    return EquippedAnimationFolder==TEXT("/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations")
        ? UppercutLongGrip.Get() : UppercutStandard.Get();
}

FString URuneSwordComponent::UppercutStatusText() const
{
    if(!IsEquipped())return TEXT("需要持剑");
    if(bUppercut)return TEXT("上挑中");
    if(!Character.IsValid()||!CanUse())return TEXT("暂不可用");
    if(IsBusy()||bGuardHeld)return TEXT("动作中");
    if(Character->IsCastBlockingLeftHandAction())return TEXT("动作占用");
    const auto* Clip=UppercutAnimation();
    if(!Clip)return UppercutLoad&&!UppercutLoad->HasLoadCompleted()?TEXT("动作准备中"):TEXT("动作未就绪");
    const auto* Mesh=Viewmodel?Viewmodel->GetSkeletalMeshAsset():nullptr;
    if(!Mesh||Clip->GetSkeleton()!=Mesh->GetSkeleton())return TEXT("动作未就绪");
    return FString();
}

bool URuneSwordComponent::CanBeginUppercut() const
{
    return UppercutStatusText().IsEmpty();
}

bool URuneSwordComponent::BeginUppercut()
{
    if(!CanBeginUppercut())return false;
    UAnimSequence* Clip=UppercutAnimation();
    // User-directed animation and forward step: no hit query, stamina payment,
    // attack-rate scaling, training event or independently persisted cooldown.
    if(bInspecting)CancelAction();
    bUppercut=true;
    // The authored release frame drives both the one-shot sword cue and stride.
    // The skill still never enters normal attack hit logic.
    bSwingCuePlayed=false;
    ContactStart=RuneSwordUppercutMotion::ReleaseStart;
    bLungeStarted=bLungeBlocked=false;
    LungeDirection=FVector::ZeroVector;
    bQueuedAttack=bQueuedQuickCombat=false;
    ImpactAge=1.f;
    StopRift();
    ScheduleWalkInspect(true);
    Animations.Add(TEXT("Uppercut"),Clip);
    SetClip(TEXT("Uppercut"),false);
    return true;
}
