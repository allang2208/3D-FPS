#include "../FPSGAMECharacter.h"
#include "AKMAttachmentVisual.h"
#include "QBZ191Attachments.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"

void AFPSGAMECharacter::InitializeCantedGripAnimations()
{
    CantedGripAnimations.Reset();
    if(!bUsingM4Infima&&!AKMSoviet::Matches(AKMViewmodel))return;
    const TPair<UAnimSequence*,const TCHAR*> Clips[]={
        {IdleAnimation,TEXT("idle")},{AimAnimation,TEXT("aim")},
        {FireAnimation,TEXT("fire")},{AimFireAnimation,TEXT("aim_fire")},
        {EquipAnimation,TEXT("equip")},{ReloadAnimation,TEXT("reload")},
        {ReloadEmptyAnimation,TEXT("reload_empty")},{DrumReloadAnimation,TEXT("drum_reload")},
        {DrumReloadEmptyAnimation,TEXT("drum_reload_empty")}};
    for(const auto& Pair:Clips)
    {
        if(bUseQBZ191&&!Pair.Key)continue;
        const FString Path=bUseQBZ191?QBZ191Attachments::AnimationPath(TEXT("canted"),Pair.Value):AKMSoviet::Matches(AKMViewmodel)?AKMAttachment::GripAnimationPath(TEXT("canted"),Pair.Value):FString::Printf(TEXT("/Game/Weapons/M4VREGripExtensions/Canted/A_M4_Canted_%s"),Pair.Value);
        auto* Clip=LoadObject<UAnimSequence>(nullptr,*Path);
        if(Pair.Key&&Clip&&FMath::IsNearlyEqual(Pair.Key->GetPlayLength(),Clip->GetPlayLength(),.001f))CantedGripAnimations.Add(Pair.Key,Clip);
        else UE_LOG(LogTemp,Error,TEXT("CANTED_GRIP: missing or mismatched clip %s"),*Path);
    }
}

void AFPSGAMECharacter::SetCantedForegrip(bool bEnabled)
{
    if(bUseQBZ191){CantedForegrip=QBZ191Attachments::Configure(this,AKMViewmodel,CantedForegrip,TEXT("canted"),(bEnabled)&&bInventoryWeaponReady);return;}
    if(AKMSoviet::Matches(AKMViewmodel)){CantedForegrip=AKMAttachment::Configure(this,AKMViewmodel,CantedForegrip,TEXT("canted"),bEnabled&&bInventoryWeaponReady);return;}
    const bool Enabled=bEnabled&&bUsingM4Infima&&bInventoryWeaponReady;
    if(CantedForegrip)CantedForegrip->SetVisibility(false);
    if(!Enabled)return;
    auto* Rifle=AKMViewmodel->GetSkeletalMeshAsset();
    if(!Rifle)return;
    const auto& Ref=Rifle->GetRefSkeleton();
    for(const TCHAR* Name:{TEXT("WPN_root"),TEXT("WPN_RearSight"),TEXT("WPN_FrontSight")})
        if(Ref.FindBoneIndex(Name)==INDEX_NONE)return;
    if(!CantedForegrip)
    {
        auto* HandstopMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/M4CantedForegrip/SM_CantedForegrip"));
        if(!HandstopMesh){UE_LOG(LogTemp,Error,TEXT("CANTED_GRIP: missing mesh"));return;}
        CantedForegrip=NewObject<UStaticMeshComponent>(this,TEXT("M4CantedForegrip"));
        CantedForegrip->SetStaticMesh(HandstopMesh);
        CantedForegrip->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));
        CantedForegrip->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        CantedForegrip->SetCastShadow(false);CantedForegrip->bReceivesDecals=false;
        CantedForegrip->RegisterComponent();
    }
    auto Bone=[&](const TCHAR* Name){FTransform T=FTransform::Identity;for(int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE;I=Ref.GetParentIndex(I))T=T*Ref.GetRefBonePose()[I];return T;};
    const auto Root=Bone(TEXT("WPN_root")),Rear=Bone(TEXT("WPN_RearSight")),Front=Bone(TEXT("WPN_FrontSight"));
    const FVector Forward=(Front.GetLocation()-Rear.GetLocation()).GetSafeNormal();
    const FVector Up=Rear.GetRotation().GetAxisZ();
    // Visual mount measured in the current M4 export's sight frame. Asset pivot
    // is the top of its saddle, with X forward and Z up; UE units are cm.
    const FTransform Mount(FRotationMatrix::MakeFromXZ(Forward,Up).ToQuat(),Rear.GetLocation()+Forward*27.f-Up*8.05f);
    CantedForegrip->SetRelativeTransform(Mount.GetRelativeTransform(Root));
    CantedForegrip->SetVisibility(true);
}

bool AFPSGAMECharacter::HasCantedForegrip() const
{
    return CantedForegrip&&CantedForegrip->IsVisible()&&CantedForegrip->GetStaticMesh();
}
