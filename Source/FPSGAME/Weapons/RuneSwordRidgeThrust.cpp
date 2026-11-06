#include "RuneSwordComponent.h"
#include "HighlandRidgeThrust.h"
#include "HighlandRidgeGatherComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "GunsmithSystem.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Animation/AnimSequence.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Components/SkeletalMeshComponent.h"

bool HighlandRidgeThrust::Installed(const UGunsmithSystem* Smith,const FColdSteelItem* Item)
{
    return Item&&Item->Definition==TEXT("ue_highland_claymore")&&Smith&&
        Smith->Installed(*Item).FindRef(TEXT("blade_1"))==TEXT("highland_ridge_piercer");
}

float URuneSwordComponent::ActiveRidgeRangeScale() const
{
    return bAzureDragonEquipped&&GetWorld()->GetTimeSeconds()<AzureDragonActiveUntil?AzureDragonReachMultiplier:1.f;
}

bool URuneSwordComponent::UsesRidgeSprintCarry() const
{
    return Animations.Contains(HighlandRidgeThrust::Charge)&&IsTacticalSprintClip(CurrentClip);
}

void URuneSwordComponent::RefreshRidgeThrust(const FColdSteelItem* Item)
{
    using namespace HighlandRidgeThrust;
    if(!Character.IsValid()||!Character->IsLocallyControlled())return;
    const auto* Smith=GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const bool Installed=HighlandRidgeThrust::Installed(Smith,Item);
    // A null charge entry means this particular load is already in flight.
    if(Installed==Animations.Contains(Charge))return;
    if(bCharging||bReturningCharge||(bAttacking&&(bHeavyAttack||IsRelease(CurrentClip))))CancelAction();
    if(!Installed)
    {
        if(RidgeGather){RidgeGather->DestroyComponent();RidgeGather=nullptr;}
        Animations.Remove(Charge);Animations.Remove(Release);Animations.Remove(Counter);
        Animations.Remove(Finisher);Animations.Remove(Dash);
        return;
    }
    if(!RidgeGather&&GetNetMode()!=NM_DedicatedServer)
        RidgeGather=UHighlandRidgeGatherComponent::CreateFor(GetOwner(),true);
    Animations.Add(Charge,nullptr);
    const FString Folder=EquippedAnimationFolder,Weapon=Item->InstanceId;
    const FString Variant=Folder.EndsWith(TEXT("LongGripAnimations"))?TEXT("LongGrip"):TEXT("Standard");
    TArray<FSoftObjectPath> Paths;
    for(const TCHAR* Phase:{TEXT("Charge"),TEXT("Release"),TEXT("Counter")})
    {
        const FString Name=TEXT("A_Highland_Ridge_")+Variant+TEXT("_")+Phase;
        Paths.Emplace(TEXT("/Game/Weapons/HighlandClaymore20260922/RidgeThrust20261105/")+Name+TEXT(".")+Name);
    }
    UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Weapon,Folder,Paths]()
    {
        if(InstanceId!=Weapon||EquippedAnimationFolder!=Folder||!Animations.Contains(Charge))return;
        const FName Roles[]={Charge,Release,Counter};
        const auto* Mesh=Viewmodel?Viewmodel->GetSkeletalMeshAsset():nullptr;
        for(int32 I=0;I<Paths.Num();++I)
        {
            auto* Seq=Cast<UAnimSequence>(Paths[I].ResolveObject());
            if(Seq && Mesh && Mesh->GetSkeleton()==Seq->GetSkeleton())Animations.Add(Roles[I],Seq);
            else UE_LOG(LogTemp,Error,TEXT("Ridge heavy motion unavailable: %s"),*Paths[I].ToString());
        }
        if(auto* ReadyThrust=Animations.FindRef(Counter).Get())
        {
            Animations.Add(Finisher,ReadyThrust);
            Animations.Add(Dash,ReadyThrust);
        }
    }));
}

void URuneSwordComponent::PresentRidgeGather()
{
    if(!RidgeGather)return;
    if(!bAttacking||!HighlandRidgeThrust::IsRelease(CurrentClip)||!CanPresent()||!CanUse(true))
    {RidgeGather->Hide();return;}
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    FVector Base,Tip;
    if((Body&&Body->IsThirdPersonViewEnabled())||!GetFireMagicBladePoints(Base,Tip))
    {RidgeGather->Hide();return;}
    const float Lead=HighlandRidgeThrust::LeadFor(CurrentClip);
    const float Peak=HighlandRidgeThrust::ToWall(Lead+HighlandRidgeThrust::ContactEnd,Lead,SwingRate);
    RidgeGather->Present(Character->GetMeleeAimTransform(),Tip,(Tip-Base).GetSafeNormal(),
        HighlandRidgeThrust::ToWall(Elapsed,Lead,SwingRate)-Peak,FMath::Min(.22f,Peak));
}
