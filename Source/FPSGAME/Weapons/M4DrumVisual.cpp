#include "../FPSGAMECharacter.h"
#include "AKMAttachmentVisual.h"
#include "QBZ191Attachments.h"
#include "ASH12WeaponAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Camera/CameraComponent.h"

void AFPSGAMECharacter::UpdateGunsmithCapture(USceneCaptureComponent2D* Capture,bool bAim)
{
    if(!Capture)return;
    Capture->ShowOnlyComponents.Reset();Capture->ShowOnlyComponent(AKMViewmodel);
    TArray<USceneComponent*> CapturedChildren;AKMViewmodel->GetChildrenComponents(true,CapturedChildren);
    for(auto* Child:CapturedChildren)if(auto* Primitive=Cast<UPrimitiveComponent>(Child))Capture->ShowOnlyComponent(Primitive);
    const auto CameraTransform=FirstPersonCamera->GetComponentTransform();
    Capture->SetWorldTransform(CameraTransform);
    if(!bAim)Capture->SetWorldLocation(CameraTransform.TransformPosition(FVector(-10,-20,-2)));
    Capture->FOVAngle=bAim?FirstPersonCamera->FieldOfView:65.f;
}
#include "Components/BoxComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"

void AFPSGAMECharacter::SetGunsmithInspection(bool bInspect)
{
    bGunsmithInspection=bInspect&&(bUsingM4Infima||AKMSoviet::Matches(AKMViewmodel));
    const auto* WeaponMesh=AKMViewmodel->GetSkeletalMeshAsset();if(!WeaponMesh)return;
    if(const auto* Render=WeaponMesh->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(WeaponMesh->GetMaterials().IsValidIndex(M)&&WeaponMesh->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("Manny")))
                    AKMViewmodel->ShowMaterialSection(M,S,!bGunsmithInspection,L);
            }
}

void AFPSGAMECharacter::SetGunsmithMagazineAttachment(const FString& Id)
{
    bool bDrum=Id==TEXT("large_drum");
    bool bExtMag=Id==TEXT("ext_mag");
    if (IsPistolWeapon()) { MagazineAttachmentId.Reset(); return; }
    const bool bRifle=bUsingM4Infima||AKMSoviet::Matches(AKMViewmodel)||bUseQBZ191;
    MagazineAttachmentId=(bDrum||bExtMag)&&bRifle&&bInventoryWeaponReady?Id:FString();
    // Preserve the historical drum gating exactly; the universal extended
    // magazine uses each rifle's own factory-derived mesh.
    bDrum=bDrum&&(bUsingM4Infima||AKMSoviet::Matches(AKMViewmodel))&&bInventoryWeaponReady;
    bExtMag=MagazineAttachmentId==TEXT("ext_mag");
    auto* WeaponMesh=AKMViewmodel->GetSkeletalMeshAsset();if(!WeaponMesh)return;
    if(bUseQBZ191&&bDrum){
        LargeDrum=QBZ191Attachments::ConfigureFitted(this,AKMViewmodel,LargeDrum,TEXT("drum"),true,TEXT("WPN_SOCKET_Magazine"));
        DrumMount=FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f));
    }
    if(AKMSoviet::Matches(AKMViewmodel)&&bDrum){
        LargeDrum=AKMAttachment::Configure(this,AKMViewmodel,LargeDrum,TEXT("drum"),true,TEXT("WPN_SOCKET_Magazine"));
        DrumMount=FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f));
    }
    // AKM already configured its own socket-space drum above. Do not replace
    // that mesh/contact frame with the M4's mesh-space drum afterward.
    if(bDrum&&!bUseQBZ191&&!AKMSoviet::Matches(AKMViewmodel))
    {
        auto* Asset=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum"));
        if(!Asset){UE_LOG(LogTemp,Error,TEXT("M4_DRUM: missing mesh"));return;}
        // Always re-apply the drum mesh: the shared component may still hold
        // the extended-magazine mesh after switching options in one session.
        if(!LargeDrum)
        {
            LargeDrum=NewObject<UStaticMeshComponent>(this,TEXT("M4LargeDrum"));
            LargeDrum->SetCollisionEnabled(ECollisionEnabled::NoCollision);LargeDrum->SetCastShadow(false);LargeDrum->bReceivesDecals=false;
            LargeDrum->SetupAttachment(AKMViewmodel,TEXT("WPN_SOCKET_Magazine"));LargeDrum->RegisterComponent();
        }
        if(LargeDrum->GetStaticMesh()!=Asset)LargeDrum->EmptyOverrideMaterials();
        LargeDrum->SetStaticMesh(Asset);
        const auto& Ref=WeaponMesh->GetRefSkeleton();FTransform Bone=FTransform::Identity;
        for(int32 I=Ref.FindBoneIndex(TEXT("WPN_SOCKET_Magazine"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Bone=Bone*Ref.GetRefBonePose()[I];
        DrumMount=FTransform::Identity.GetRelativeTransform(Bone);LargeDrum->SetRelativeTransform(DrumMount);
    }
    if(bExtMag)
    {
        // Each rifle takes its own factory magazine shape, so each gets its own
        // asset: QBZ-191 polymer, M4 PMAG, AKM stamped steel.
        auto* Asset=LoadObject<UStaticMesh>(nullptr,bUseASH12
            ?ASH12WeaponAssets::ExtendedMagazineMeshPath
            :bUseQBZ191
            ?TEXT("/Game/Weapons/ExtMagRemodel20260919/SM_ExtMag_QBZ40_Remodel.SM_ExtMag_QBZ40_Remodel")
            :AKMSoviet::Matches(AKMViewmodel)
                ?TEXT("/Game/Weapons/ExtMagContinuity20260919/SM_ExtMag_AKM40_Continuous.SM_ExtMag_AKM40_Continuous")
                :TEXT("/Game/Weapons/M4GridUnified20260919/SM_M4_ExtMag40_Grid.SM_M4_ExtMag40_Grid"));
        if(!Asset){UE_LOG(LogTemp,Error,TEXT("EXT_MAG: missing mesh"));return;}
        if(!LargeDrum)
        {
            LargeDrum=NewObject<UStaticMeshComponent>(this,TEXT("GunsmithExtMag"));
            LargeDrum->SetCollisionEnabled(ECollisionEnabled::NoCollision);LargeDrum->SetCastShadow(false);LargeDrum->bReceivesDecals=false;
            LargeDrum->SetupAttachment(AKMViewmodel,TEXT("WPN_SOCKET_Magazine"));LargeDrum->RegisterComponent();
        }
        if(LargeDrum->GetStaticMesh()!=Asset)LargeDrum->EmptyOverrideMaterials();
        LargeDrum->SetStaticMesh(Asset);
        // ExtMagPattern20260919 preserves each factory magazine's mesh-space
        // upper shell and feed section, extending only the lower body. The
        // factory magazine is skinned 100% to WPN_SOCKET_Magazine, so retain
        // its bind-chain inverse for the replacement throughout the reload.
        // Use the drum's own accumulation verbatim: it is the only seat formula
        // in this file that has been verified in game. A parent-first product of
        // the same ref poses (the "textbook" socket transform) reads differently
        // here and buried the magazine inside the receiver instead of the well,
        // so both are logged for comparison.
        const auto& Ref=WeaponMesh->GetRefSkeleton();
        TArray<int32> MagChain;
        FTransform Bone=FTransform::Identity;
        for(int32 I=Ref.FindBoneIndex(TEXT("WPN_SOCKET_Magazine"));I!=INDEX_NONE;I=Ref.GetParentIndex(I)){MagChain.Add(I);Bone=Bone*Ref.GetRefBonePose()[I];}
        FTransform ParentFirst=FTransform::Identity;
        for(int32 K=MagChain.Num()-1;K>=0;--K)ParentFirst=ParentFirst*Ref.GetRefBonePose()[MagChain[K]];
        // All three magazines are authored in their own rifle's mesh frame: each
        // part is that rifle's factory magazine lengthened in place, so the
        // accepted mounting (the socket chain inverse, the same one the accepted
        // large drum uses) seats the magazine exactly where the factory magazine
        // sits and lets it ride the same bone through the reload. The AKM used to
        // be authored in the socket frame instead, which put it about 35 cm
        // outside the well in game (logged as frame=socket in that round).
        LargeDrum->SetRelativeTransform(FTransform::Identity.GetRelativeTransform(Bone));
        const FBoxSphereBounds SeatBounds=Asset->GetBounds().TransformBy(LargeDrum->GetComponentTransform());
        UE_LOG(LogTemp,Display,TEXT("EXT_MAG: attached id=%s mesh=%s frame=%s rel_loc=%s rel_scale=%s bind_scale=%s seat_t=%s parentfirst_t=%s world_loc=%s world_extent=%s parent=%s parent_loc=%s weapon_loc=%s socket_ok=%d skel=%s"),
            *MagazineAttachmentId,*Asset->GetName(),TEXT("weapon"),
            *LargeDrum->GetRelativeLocation().ToString(),*LargeDrum->GetRelativeScale3D().ToString(),
            *Bone.GetScale3D().ToString(),*Bone.GetLocation().ToString(),*ParentFirst.GetLocation().ToString(),
            *LargeDrum->GetComponentLocation().ToString(),*SeatBounds.BoxExtent.ToString(),
            LargeDrum->GetAttachParent()?*LargeDrum->GetAttachParent()->GetName():TEXT("none"),
            LargeDrum->GetAttachParent()?*LargeDrum->GetAttachParent()->GetComponentLocation().ToString():TEXT("-"),
            *AKMViewmodel->GetComponentLocation().ToString(),
            AKMViewmodel->DoesSocketExist(TEXT("WPN_SOCKET_Magazine"))?1:0,
            WeaponMesh?*WeaponMesh->GetName():TEXT("none"));
        DrumMount=LargeDrum->GetRelativeTransform();
    }
    bDrumVisual=bDrum;if(LargeDrum)LargeDrum->SetVisibility(bDrum||bExtMag);
    // Hide the complete original magazine, preserving the receiver and all skin weights.
    if(const auto* Render=WeaponMesh->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(WeaponMesh->GetMaterials().IsValidIndex(M)&&WeaponMesh->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("Magazine")))
                    AKMViewmodel->ShowMaterialSection(M,S,!(bDrum||bExtMag),L);
            }
}
bool AFPSGAMECharacter::ValidateDrumAttachment() const
{
    if(!bDrumVisual||!LargeDrum||LargeDrum->IsVisible()==bDrumMagazineHidden)return false;
    const auto Expected=DrumMount*AKMViewmodel->GetSocketTransform(TEXT("WPN_SOCKET_Magazine"));
    if(!LargeDrum->GetComponentScale().Equals(Expected.GetScale3D(),.002f)||!LargeDrum->GetComponentScale().Equals(FVector::OneVector,.005f))return false;
    if(!LargeDrum->GetComponentLocation().Equals(Expected.GetLocation(),.02f)||LargeDrum->GetComponentQuat().AngularDistance(Expected.GetRotation())>.002f)return false;
    const auto* WeaponMesh=AKMViewmodel->GetSkeletalMeshAsset();bool Found=false;
    for(int32 M=0;M<WeaponMesh->GetMaterials().Num();++M)
        if(WeaponMesh->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("Magazine")))
        {Found=true;if(!AKMViewmodel->IsMaterialSectionShown(M,0))continue;return false;}
    return Found;
}

void AFPSGAMECharacter::UpdateDrumDropVisual()
{
    if(!LargeDrum)return;
    if(MagazineAttachmentId==TEXT("ext_mag"))
    {
        // The universal magazine is socket-bound and rides the authored
        // reload path; no drum drop choreography.
        bDrumReleasedDuringReload=false;bDrumMagazineHidden=false;
        LargeDrum->SetVisibility(true);return;
    }
    if(!bDrumInstalled||!IsReloading())
    {
        bDrumReleasedDuringReload=false;bDrumMagazineHidden=false;
        LargeDrum->SetVisibility(bDrumVisual);return;
    }
    const float Frame=ReloadSourceTime(WeaponStateElapsed)*60.0f;
    // AKM skips the hand-pull: release from the seated socket at source frame
    // 36 / 120 Hz, while the left hand travels outside the drum to its pickup.
    const float Release=bUseQBZ191?36.f:AKMSoviet::Matches(AKMViewmodel)?18.f:(bPendingEmptyReload?14.0f:18.0f);
    const float Pickup=bUseQBZ191?49.f:AKMSoviet::Matches(AKMViewmodel)?56.f:(bPendingEmptyReload?31.0f:36.0f);
    if(Frame>=Release&&!bDrumReleasedDuringReload)
    {
        bDrumReleasedDuringReload=true;
        FActorSpawnParameters Params;Params.Owner=this;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        const FVector Center=LargeDrum->Bounds.Origin;
        if(auto* Dropped=GetWorld()->SpawnActor<AActor>(AActor::StaticClass(),Center,FRotator::ZeroRotator,Params))
        {
            auto* Body=NewObject<UBoxComponent>(Dropped,TEXT("DrumDropBody"));Dropped->SetRootComponent(Body);Body->SetBoxExtent(LargeDrum->GetStaticMesh()->GetBounds().BoxExtent*LargeDrum->GetComponentScale().GetAbs());
            Body->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Body->SetCollisionObjectType(ECC_PhysicsBody);Body->SetCollisionResponseToAllChannels(ECR_Ignore);Body->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);Body->RegisterComponent();Body->SetWorldLocationAndRotation(Center,LargeDrum->GetComponentQuat());
            auto* Visual=NewObject<UStaticMeshComponent>(Dropped,TEXT("DroppedDrumMesh"));Visual->SetStaticMesh(LargeDrum->GetStaticMesh());Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);Visual->SetCastShadow(true);Visual->SetupAttachment(Body);Visual->RegisterComponent();Visual->SetWorldTransform(LargeDrum->GetComponentTransform());
            Body->SetSimulatePhysics(true);Body->SetMassOverrideInKg(NAME_None,2.5f,true);
            const bool bAKMDrum=AKMSoviet::Matches(AKMViewmodel);
            Body->SetPhysicsLinearVelocity(bAKMDrum?GetVelocity()+FVector(0,0,-20.f):
                GetVelocity()+FirstPersonCamera->GetRightVector()*-180.f+FirstPersonCamera->GetForwardVector()*65.f+FVector(0,0,-110.f));
            Body->SetPhysicsAngularVelocityInDegrees(bAKMDrum?FirstPersonCamera->GetRightVector()*12.f:
                FirstPersonCamera->GetForwardVector()*140.0f+FirstPersonCamera->GetRightVector()*60.0f);Dropped->SetLifeSpan(8);
            LastDroppedDrum=Dropped;LastDrumDropStart=Center;
            ++DrumDropCount;UE_LOG(LogTemp,Display,TEXT("DRUM_DROP: released frame=%.2f count=%d"),Frame,DrumDropCount);
        }
    }
    bDrumMagazineHidden=bDrumReleasedDuringReload&&Frame<Pickup;
    LargeDrum->SetVisibility(bDrumVisual&&!bDrumMagazineHidden);
}
