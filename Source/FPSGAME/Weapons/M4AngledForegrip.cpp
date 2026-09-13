#include "../FPSGAMECharacter.h"
#include "AKMAttachmentVisual.h"
#include "QBZ191Attachments.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"

void AFPSGAMECharacter::InitializeForegripAnimations()
{
    ForegripAnimations.Reset();
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
        const FString Path=AKMSoviet::Matches(AKMViewmodel)?FString::Printf(TEXT("/Game/Weapons/AKMIntegration/SovietFab/Attachments/angled/A_AKM_angled_%s"),Pair.Value):FString::Printf(TEXT("/Game/Weapons/M4ForegripWristNatural/A_M4_Foregrip_%s"),Pair.Value);
        const FString ResolvedPath=bUseQBZ191?QBZ191Attachments::AnimationPath(TEXT("angled"),Pair.Value):AKMSoviet::Matches(AKMViewmodel)?AKMAttachment::GripAnimationPath(TEXT("angled"),Pair.Value):Path;
        auto* Clip=LoadObject<UAnimSequence>(nullptr,*ResolvedPath);
        if(Pair.Key&&Clip&&FMath::IsNearlyEqual(Pair.Key->GetPlayLength(),Clip->GetPlayLength(),.001f))ForegripAnimations.Add(Pair.Key,Clip);
        else UE_LOG(LogTemp,Error,TEXT("FOREGRIP: missing or mismatched clip %s"),*Path);
    }
}

void AFPSGAMECharacter::SetAngledForegrip(bool bEnabled)
{
    if(bUseQBZ191){AngledForegrip=QBZ191Attachments::Configure(this,AKMViewmodel,AngledForegrip,TEXT("angled"),(bEnabled)&&bInventoryWeaponReady);return;}
    if(AKMSoviet::Matches(AKMViewmodel)){AngledForegrip=AKMAttachment::Configure(this,AKMViewmodel,AngledForegrip,TEXT("angled"),bEnabled&&bInventoryWeaponReady);return;}
    bEnabled=bEnabled&&bUsingM4Infima&&bInventoryWeaponReady;
    if(AngledForegrip)AngledForegrip->SetVisibility(false);
    if(!bEnabled)return;
    auto* Rifle=AKMViewmodel->GetSkeletalMeshAsset();if(!Rifle)return;
    const auto& Ref=Rifle->GetRefSkeleton();const int32 Root=Ref.FindBoneIndex(TEXT("WPN_root"));if(Root==INDEX_NONE)return;
    if(!AngledForegrip)
    {
        auto* GripMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/M4AngledForegripCompact75/SM_M4_AngledForegrip"));if(!GripMesh)return;
        AngledForegrip=NewObject<UStaticMeshComponent>(this,TEXT("M4AngledForegrip"));AngledForegrip->SetStaticMesh(GripMesh);
        AngledForegrip->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));AngledForegrip->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        AngledForegrip->SetCastShadow(false);AngledForegrip->bReceivesDecals=false;AngledForegrip->RegisterComponent();
    }
    // Mesh is exported in the rifle bind space. Cancel that space once, then follow WPN_root.
    FTransform Bone=FTransform::Identity;
    for(int32 I=Root;I!=INDEX_NONE;I=Ref.GetParentIndex(I))Bone=Bone*Ref.GetRefBonePose()[I];
    AngledForegrip->SetRelativeTransform(FTransform::Identity.GetRelativeTransform(Bone));AngledForegrip->SetVisibility(true);
}

bool AFPSGAMECharacter::HasAngledForegrip() const
{
    return AngledForegrip&&AngledForegrip->IsVisible()&&AngledForegrip->GetStaticMesh();
}
