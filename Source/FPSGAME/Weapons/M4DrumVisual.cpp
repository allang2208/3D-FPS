#include "../FPSGAMECharacter.h"
#include "AKMAttachmentVisual.h"
#include "QBZ191Attachments.h"
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

void AFPSGAMECharacter::SetGunsmithDrum(bool bDrum)
{
    bDrum=bDrum&&(bUsingM4Infima||AKMSoviet::Matches(AKMViewmodel))&&bInventoryWeaponReady;
    auto* WeaponMesh=AKMViewmodel->GetSkeletalMeshAsset();if(!WeaponMesh)return;
    if(bUseQBZ191){
        LargeDrum=QBZ191Attachments::ConfigureFitted(this,AKMViewmodel,LargeDrum,TEXT("drum"),bDrum,TEXT("WPN_SOCKET_Magazine"));
        DrumMount=FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f));
    }
    if(AKMSoviet::Matches(AKMViewmodel)){
        LargeDrum=AKMAttachment::Configure(this,AKMViewmodel,LargeDrum,TEXT("drum"),bDrum,TEXT("WPN_SOCKET_Magazine"));
        DrumMount=FTransform(FQuat::Identity,FVector::ZeroVector,FVector(.01f));
    }
    if(bDrum&&!LargeDrum&&!bUseQBZ191)
    {
        auto* Asset=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum"));
        if(!Asset){UE_LOG(LogTemp,Error,TEXT("M4_DRUM: missing mesh"));return;}
        LargeDrum=NewObject<UStaticMeshComponent>(this,TEXT("M4LargeDrum"));LargeDrum->SetStaticMesh(Asset);
        LargeDrum->SetCollisionEnabled(ECollisionEnabled::NoCollision);LargeDrum->SetCastShadow(false);LargeDrum->bReceivesDecals=false;
        LargeDrum->SetupAttachment(AKMViewmodel,TEXT("WPN_SOCKET_Magazine"));LargeDrum->RegisterComponent();
        const auto& Ref=WeaponMesh->GetRefSkeleton();FTransform Bone=FTransform::Identity;
        for(int32 I=Ref.FindBoneIndex(TEXT("WPN_SOCKET_Magazine"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Bone=Bone*Ref.GetRefBonePose()[I];
        DrumMount=FTransform::Identity.GetRelativeTransform(Bone);LargeDrum->SetRelativeTransform(DrumMount);
    }
    bDrumVisual=bDrum;if(LargeDrum)LargeDrum->SetVisibility(bDrum);
    // Hide the complete original magazine, preserving the receiver and all skin weights.
    if(const auto* Render=WeaponMesh->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(WeaponMesh->GetMaterials().IsValidIndex(M)&&WeaponMesh->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("Magazine")))
                    AKMViewmodel->ShowMaterialSection(M,S,!bDrum,L);
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
    if(!bDrumInstalled||!IsReloading())
    {
        bDrumReleasedDuringReload=false;bDrumMagazineHidden=false;
        LargeDrum->SetVisibility(bDrumVisual);return;
    }
    const float Frame=ReloadSourceTime(WeaponStateElapsed)*60.0f;
    // AKM: the authored 120 Hz pull clears the magazine well before fingers open at frame 86.
    const float Release=bUseQBZ191?36.f:AKMSoviet::Matches(AKMViewmodel)?43.f:(bPendingEmptyReload?14.0f:18.0f);
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
            Body->SetPhysicsLinearVelocity(GetVelocity()+FirstPersonCamera->GetRightVector()*(bAKMDrum?-85.f:-180.f)+FirstPersonCamera->GetForwardVector()*(bAKMDrum?45.f:65.f)+FVector(0,0,bAKMDrum?-140.f:-110.f));
            Body->SetPhysicsAngularVelocityInDegrees(FirstPersonCamera->GetForwardVector()*140.0f+FirstPersonCamera->GetRightVector()*60.0f);Dropped->SetLifeSpan(8);
            LastDroppedDrum=Dropped;LastDrumDropStart=Center;
            ++DrumDropCount;UE_LOG(LogTemp,Display,TEXT("DRUM_DROP: released frame=%.2f count=%d"),Frame,DrumDropCount);
        }
    }
    bDrumMagazineHidden=bDrumReleasedDuringReload&&Frame<Pickup;
    LargeDrum->SetVisibility(bDrumVisual&&!bDrumMagazineHidden);
}
