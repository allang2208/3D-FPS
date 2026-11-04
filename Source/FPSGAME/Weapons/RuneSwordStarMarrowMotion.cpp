#include "RuneSwordComponent.h"
#include "StarMarrowChargeMotion.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"

void URuneSwordComponent::LoadStarMarrowMotion(const FString& Definition,const FString& Folder)
{
    if(Definition!=TEXT("ue_frost_crystal_sword")||!Character.IsValid()||!Character->IsLocallyControlled())return;
    const FString Variant=Folder.EndsWith(TEXT("LongGripAnimations"))?TEXT("LongGrip"):TEXT("Standard");
    const FSoftObjectPath Path(TEXT("/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeMotion20261103/")
        +Variant+TEXT("/A_StarMarrow_Charge.A_StarMarrow_Charge"));
    const FString RequestedInstance=InstanceId;
    StarMarrowMotionLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Path,
        FStreamableDelegate::CreateWeakLambda(this,[this,Path,RequestedInstance,Folder]()
        {
            if(InstanceId!=RequestedInstance||EquippedAnimationFolder!=Folder)return;
            if(auto* Clip=Cast<UAnimSequence>(Path.ResolveObject()))Animations.Add(TEXT("StarMarrowCharge"),Clip);
            else UE_LOG(LogTemp,Error,TEXT("StarMarrow charge motion missing: %s"),*Path.ToString());
        }));
}

bool URuneSwordComponent::IsStarMarrowChargeMotionReady() const
{return Animations.FindRef(TEXT("StarMarrowCharge"))!=nullptr;}

bool URuneSwordComponent::IsStarMarrowChargeMotionPlaying() const
{return bEquipping&&CurrentClip==TEXT("StarMarrowCharge");}

bool URuneSwordComponent::BeginStarMarrowChargeMotion(float Age)
{
    if(IsStarMarrowChargeMotionPlaying())return true; // Replication confirms the predicted action without restarting it.
    if(!Character.IsValid()||!Character->IsLocallyControlled()||!IsEquipped()||!CanUse()||IsBusy()
        ||!IsStarMarrowChargeMotionReady()||Age>=StarMarrowChargeMotion::Duration)return false;
    if(bInspecting)CancelAction();
    Character->ExitSprintForWeapon();
    bEquipping=true;bQueuedAttack=false;
    SetClip(TEXT("StarMarrowCharge"),false);
    Elapsed=FMath::Max(0.f,Age);SamplePose(Elapsed);
    return true;
}

void URuneSwordComponent::CancelStarMarrowChargeMotion()
{if(IsStarMarrowChargeMotionPlaying())CancelAction();}
