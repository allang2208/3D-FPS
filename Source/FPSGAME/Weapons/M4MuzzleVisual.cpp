#include "../FPSGAMECharacter.h"
#include "AKMSovietCalibration.h"
#include "AKMAttachmentVisual.h"
#include "QBZ191Attachments.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Camera/CameraComponent.h"
#include "Sound/SoundBase.h"

void AFPSGAMECharacter::SetGunsmithMuzzle(const FString& Variant)
{
    const bool Valid=Variant==TEXT("true")||Variant==TEXT("brake")||Variant==TEXT("titanium_brake");
    if(bUseQBZ191){
        const bool Enabled=Valid&&bInventoryWeaponReady;
        const FString Key=Variant==TEXT("true")?TEXT("suppressor"):Variant;
        MuzzleAttachment=QBZ191Attachments::ConfigureFitted(this,AKMViewmodel,MuzzleAttachment,Key,Enabled);
        MuzzleVariant=Enabled?Variant:TEXT("");
        if(Enabled&&MuzzleAttachment){
            const auto Bounds=MuzzleAttachment->GetStaticMesh()->GetBounds();
            MuzzleLocalAxis=FVector::RightVector;
            MuzzleLocalTip=FVector(.0759f,Bounds.Origin.Y+Bounds.BoxExtent.Y,6.0775f);
        }
        if(auto* Rifle=AKMViewmodel->GetSkeletalMeshAsset())if(const auto* Render=Rifle->GetResourceForRendering())
            for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S){
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(Rifle->GetMaterials().IsValidIndex(M)&&Rifle->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("Flash_Hider")))AKMViewmodel->ShowMaterialSection(M,S,!Enabled,L);
            }
        if(!SuppressedFireSound)SuppressedFireSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed"));
        return;
    }
    if(AKMSoviet::Matches(AKMViewmodel)){
        const bool Enabled=Valid&&bInventoryWeaponReady;const FString Key=Variant==TEXT("true")?TEXT("suppressor"):Variant;
        MuzzleAttachment=AKMAttachment::Configure(this,AKMViewmodel,MuzzleAttachment,*Key,Enabled);
        MuzzleVariant=Enabled?Variant:TEXT("");
        if(Enabled&&MuzzleAttachment){const auto B=MuzzleAttachment->GetStaticMesh()->GetBounds();MuzzleLocalAxis=FVector::RightVector;MuzzleLocalTip=FVector(AKMSoviet::Muzzle.X*100.f,B.Origin.Y+B.BoxExtent.Y,AKMSoviet::Muzzle.Z*100.f);}
        if(!SuppressedFireSound)SuppressedFireSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed"));return;
    }
    const FString Desired=Valid&&bUsingM4Infima&&bInventoryWeaponReady?Variant:TEXT("");
    auto* Rifle=AKMViewmodel->GetSkeletalMeshAsset();if(!Rifle)return;
    if(!Desired.IsEmpty())
    {
        const FString Key=Desired==TEXT("true")?TEXT("suppressor"):Desired;
        const FString Path=TEXT("/Game/Weapons/M4MuzzlesV1/SM_M4_")+Key;
        auto* MuzzleMesh=LoadObject<UStaticMesh>(nullptr,*Path);if(!MuzzleMesh){UE_LOG(LogTemp,Error,TEXT("MUZZLE: missing %s"),*Path);return;}
        if(!MuzzleAttachment){MuzzleAttachment=NewObject<UStaticMeshComponent>(this,TEXT("M4MuzzleAttachment"));MuzzleAttachment->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));MuzzleAttachment->SetCollisionEnabled(ECollisionEnabled::NoCollision);MuzzleAttachment->SetCastShadow(false);MuzzleAttachment->RegisterComponent();}
        MuzzleAttachment->SetStaticMesh(MuzzleMesh);
        const auto B=MuzzleMesh->GetBounds();int32 Axis=0;if(B.BoxExtent.Y>B.BoxExtent.X)Axis=1;if(B.BoxExtent.Z>B.BoxExtent[Axis])Axis=2;
        MuzzleLocalAxis=FVector::ZeroVector;MuzzleLocalAxis[Axis]=B.Origin[Axis]>=0?1.f:-1.f;
        MuzzleLocalTip=MuzzleLocalAxis*(FMath::Abs(B.Origin[Axis])+B.BoxExtent[Axis]);
        const auto& Ref=Rifle->GetRefSkeleton();
        auto Bone=[&](const TCHAR* Name){FTransform T=FTransform::Identity;for(int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE;I=Ref.GetParentIndex(I))T=T*Ref.GetRefBonePose()[I];return T;};
        const auto Root=Bone(TEXT("WPN_root")),Rear=Bone(TEXT("WPN_RearSight")),Front=Bone(TEXT("WPN_FrontSight")),Muzzle=Bone(TEXT("WPN_SOCKET_Muzzle"));
        const FVector Forward=(Front.GetLocation()-Rear.GetLocation()).GetSafeNormal();
        const FVector Up=Rear.GetRotation().GetAxisZ();
        const FQuat SourceFrame=FRotationMatrix::MakeFromXZ(MuzzleLocalAxis,FVector::UpVector).ToQuat();
        const FQuat TargetFrame=FRotationMatrix::MakeFromXZ(Forward,Up).ToQuat();
        // Measured from the current export's factory flash-hider rear rim to its socket.
        const FTransform Mount(TargetFrame*SourceFrame.Inverse(),Muzzle.GetLocation()-Forward*4.83633f,FVector::OneVector);
        MuzzleAttachment->SetRelativeTransform(Mount.GetRelativeTransform(Root));
        if(!SuppressedFireSound)SuppressedFireSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed"));
    }
    MuzzleVariant=Desired;if(MuzzleAttachment)MuzzleAttachment->SetVisibility(!Desired.IsEmpty());
    if(const auto* Render=Rifle->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
    {
        const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
        if(Rifle->GetMaterials().IsValidIndex(M)&&Rifle->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("Flash_Hider")))AKMViewmodel->ShowMaterialSection(M,S,Desired.IsEmpty(),L);
    }
}
FVector AFPSGAMECharacter::GetEffectiveMuzzleLocation() const
{
    if(AKMSoviet::Matches(AKMViewmodel)&&MuzzleVariant.IsEmpty())return AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).TransformPosition(AKMSoviet::Muzzle);
    return !MuzzleVariant.IsEmpty()&&MuzzleAttachment?MuzzleAttachment->GetComponentTransform().TransformPosition(MuzzleLocalTip):AKMViewmodel->GetSocketLocation(TEXT("WPN_SOCKET_Muzzle"));
}
FVector AFPSGAMECharacter::GetEffectiveMuzzleForward() const
{
    if(!MuzzleVariant.IsEmpty()&&MuzzleAttachment)return MuzzleAttachment->GetComponentQuat().RotateVector(MuzzleLocalAxis);
    FVector F=AKMViewmodel->GetSocketQuaternion(TEXT("WPN_SOCKET_Muzzle")).GetAxisY();
    return FVector::DotProduct(F,FirstPersonCamera->GetForwardVector())<0?-F:F;
}
