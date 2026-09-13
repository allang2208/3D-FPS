#include "../FPSGAMECharacter.h"
#include "AKMAttachmentVisual.h"
#include "QBZ191Attachments.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "VerticalGripAnimationFamily.h"

void AFPSGAMECharacter::InitializePrismGripAnimations()
{
    PrismGripAnimations.Reset();
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
        const FString Path=AKMSoviet::Matches(AKMViewmodel)?FString::Printf(TEXT("/Game/Weapons/AKMIntegration/SovietFab/Attachments/prism/A_AKM_prism_%s"),Pair.Value):VerticalGripAnimationFamily::M4ClipPath(VerticalGripAnimationFamily::EContactProfile::Prism,Pair.Value);
        const FString ResolvedPath=bUseQBZ191?QBZ191Attachments::AnimationPath(TEXT("prism"),Pair.Value):AKMSoviet::Matches(AKMViewmodel)?AKMAttachment::GripAnimationPath(TEXT("prism"),Pair.Value):Path;
        auto* Clip=LoadObject<UAnimSequence>(nullptr,*ResolvedPath);
        if(Pair.Key&&Clip&&FMath::IsNearlyEqual(Pair.Key->GetPlayLength(),Clip->GetPlayLength(),.001f))PrismGripAnimations.Add(Pair.Key,Clip);
        else UE_LOG(LogTemp,Error,TEXT("PRISM_GRIP: missing or mismatched clip %s"),*Path);
    }
}

void AFPSGAMECharacter::SetGunsmithHandstop(const FString& Variant)
{
    SetAngledForegrip(Variant==TEXT("angled_foregrip"));
    SetVerticalForegrip(Variant==TEXT("vertical_foregrip"));
    SetCantedForegrip(Variant==TEXT("canted_foregrip"));
    if(bUseQBZ191){PrismHandstop=QBZ191Attachments::Configure(this,AKMViewmodel,PrismHandstop,TEXT("prism"),(Variant==TEXT("prism_handstop"))&&bInventoryWeaponReady);return;}
    if(AKMSoviet::Matches(AKMViewmodel)){PrismHandstop=AKMAttachment::Configure(this,AKMViewmodel,PrismHandstop,TEXT("prism"),Variant==TEXT("prism_handstop")&&bInventoryWeaponReady);return;}
    const bool Enabled=Variant==TEXT("prism_handstop")&&bUsingM4Infima&&bInventoryWeaponReady;
    if(PrismHandstop)PrismHandstop->SetVisibility(false);
    if(!Enabled)return;
    auto* Rifle=AKMViewmodel->GetSkeletalMeshAsset();
    if(!Rifle)return;
    const auto& Ref=Rifle->GetRefSkeleton();
    for(const TCHAR* Name:{TEXT("WPN_root"),TEXT("WPN_RearSight"),TEXT("WPN_FrontSight")})
        if(Ref.FindBoneIndex(Name)==INDEX_NONE)return;
    if(!PrismHandstop)
    {
        auto* HandstopMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PrismHandstop"));
        if(!HandstopMesh){UE_LOG(LogTemp,Error,TEXT("PRISM_HANDSTOP: missing mesh"));return;}
        PrismHandstop=NewObject<UStaticMeshComponent>(this,TEXT("M4PrismHandstop"));
        PrismHandstop->SetStaticMesh(HandstopMesh);
        PrismHandstop->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));
        PrismHandstop->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        PrismHandstop->SetCastShadow(false);PrismHandstop->bReceivesDecals=false;
        PrismHandstop->RegisterComponent();
    }
    auto Bone=[&](const TCHAR* Name){FTransform T=FTransform::Identity;for(int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE;I=Ref.GetParentIndex(I))T=T*Ref.GetRefBonePose()[I];return T;};
    const auto Root=Bone(TEXT("WPN_root")),Rear=Bone(TEXT("WPN_RearSight")),Front=Bone(TEXT("WPN_FrontSight"));
    const FVector Forward=(Front.GetLocation()-Rear.GetLocation()).GetSafeNormal();
    const FVector Up=Rear.GetRotation().GetAxisZ();
    // Visual mount measured in the current M4 export's sight frame. Asset pivot
    // is the top of its saddle, with X forward and Z up; UE units are cm.
    const FTransform Mount(FRotationMatrix::MakeFromXZ(Forward,Up).ToQuat(),Rear.GetLocation()+Forward*27.f-Up*8.05f);
    PrismHandstop->SetRelativeTransform(Mount.GetRelativeTransform(Root));
    PrismHandstop->SetVisibility(true);
}

bool AFPSGAMECharacter::HasPrismHandstop() const
{
    return PrismHandstop&&PrismHandstop->IsVisible()&&PrismHandstop->GetStaticMesh();
}
