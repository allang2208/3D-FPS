#include "../FPSGAMECharacter.h"
#include "A762Attachments.h"
#include "PKMAttachments.h"
#include "M16Attachments.h"
#include "A762WeaponAssets.h"
#include "AKMSovietCalibration.h"
#include "AKMAttachmentVisual.h"
#include "ASH12WeaponAssets.h"
#include "M16WeaponAssets.h"
#include "QBZ191Attachments.h"
#include "TacticalSuppressorAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Camera/CameraComponent.h"
#include "Sound/SoundBase.h"

void AFPSGAMECharacter::SetGunsmithMuzzle(const FString& Variant)
{
    if (bUseDanWesson715) return;
    if (bUseM1911) { SetM1911Muzzle(Variant); return; }
    const bool bASH12Tactical = bUseASH12 && Variant == TEXT("ash12_tactical_suppressor");
    const bool bASH12Brake = bUseASH12 && Variant == TEXT("ash12_tactical_brake");
    const bool Valid=bASH12Tactical||bASH12Brake||Variant==TEXT("true")||Variant==TEXT("tactical_suppressor")||Variant==TEXT("brake")||Variant==TEXT("titanium_brake");
    const bool bPKM=PKMLowpolyWeaponAssets::Matches(AKMViewmodel);
    if (A762WeaponAssets::Matches(AKMViewmodel) || bPKM)
    {
        const bool Enabled=Valid&&bInventoryWeaponReady;
        if (Enabled)
        {
            const FString Key=Variant==TEXT("true")?TEXT("suppressor"):Variant;
            const FString Path=bPKM?PKMAttachments::MeshPath(Key):A762Attachments::MeshPath(Key);
            auto* Part=LoadObject<UStaticMesh>(nullptr,*Path);if (!Part) return;
            if (!MuzzleAttachment)
            {
                MuzzleAttachment=NewObject<UStaticMeshComponent>(this,TEXT("A762Muzzle"));MuzzleAttachment->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));
                MuzzleAttachment->SetCollisionEnabled(ECollisionEnabled::NoCollision);MuzzleAttachment->SetCastShadow(false);MuzzleAttachment->RegisterComponent();
            }
            MuzzleAttachment->EmptyOverrideMaterials();MuzzleAttachment->SetStaticMesh(Part);
            // Authored generic muzzle contract: local -Y points to the outlet.
            MuzzleLocalAxis=-FVector::RightVector;
            const double Length=Key==TEXT("tactical_suppressor")?18.68658:Key==TEXT("suppressor")?18.6:Key==TEXT("brake")?6.8:7.25;
            MuzzleLocalTip=MuzzleLocalAxis*Length;
            MuzzleAttachment->SetRelativeTransform(FTransform(FQuat(FVector::UpVector,PI),bPKM?PKMAttachments::MuzzleMount:A762WeaponAssets::MuzzleMount,FVector(.01f)));
        }
        MuzzleVariant=Enabled?Variant:FString();if (MuzzleAttachment) MuzzleAttachment->SetVisibility(Enabled);
        if (auto* Rifle=AKMViewmodel->GetSkeletalMeshAsset()) if (const auto* Render=Rifle->GetResourceForRendering())
            for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if (Rifle->GetMaterials()[M].MaterialSlotName==TEXT("M_A762_Flash_Hider") || (bPKM&&Rifle->GetMaterials()[M].MaterialSlotName.ToString().Contains(TEXT("__FactoryMuzzle")))) AKMViewmodel->ShowMaterialSection(M,S,!Enabled,L);
            }
        SuppressedFireSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed"));return;
    }
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
        SuppressedFireSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Weapons/AKM/SuppressedAudio20260921/S_AKM_Suppressed"));return;
    }
    const FString Desired=Valid&&bUsingM4Infima&&bInventoryWeaponReady?Variant:TEXT("");
    auto* Rifle=AKMViewmodel->GetSkeletalMeshAsset();if(!Rifle)return;
    if(!Desired.IsEmpty())
    {
        const FString Key=Desired==TEXT("true")?TEXT("suppressor"):Desired;
        const FString Path=bUseM16?M16Attachments::MeshPath(Key):bASH12Tactical?ASH12WeaponAssets::TacticalSuppressorMeshPath:
            bASH12Brake?ASH12WeaponAssets::TacticalBrakeMeshPath:
            Key==TEXT("tactical_suppressor")?TacticalSuppressorAssets::MeshPath(TEXT("M4")):TEXT("/Game/Weapons/M4MuzzlesV1/SM_M4_")+Key;
        auto* MuzzleMesh=LoadObject<UStaticMesh>(nullptr,*Path);if(!MuzzleMesh){UE_LOG(LogTemp,Error,TEXT("MUZZLE: missing %s"),*Path);return;}
        if(!MuzzleAttachment){MuzzleAttachment=NewObject<UStaticMeshComponent>(this,TEXT("M4MuzzleAttachment"));MuzzleAttachment->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));MuzzleAttachment->SetCollisionEnabled(ECollisionEnabled::NoCollision);MuzzleAttachment->SetCastShadow(false);MuzzleAttachment->RegisterComponent();}
        if(MuzzleAttachment->GetStaticMesh()!=MuzzleMesh)MuzzleAttachment->EmptyOverrideMaterials();
        MuzzleAttachment->SetStaticMesh(MuzzleMesh);
        const auto B=MuzzleMesh->GetBounds();int32 Axis=0;if(B.BoxExtent.Y>B.BoxExtent.X)Axis=1;if(B.BoxExtent.Z>B.BoxExtent[Axis])Axis=2;
        MuzzleLocalAxis=FVector::ZeroVector;MuzzleLocalAxis[Axis]=B.Origin[Axis]>=0?1.f:-1.f;
        MuzzleLocalTip=MuzzleLocalAxis*(FMath::Abs(B.Origin[Axis])+B.BoxExtent[Axis]);
        if(bASH12Tactical||bASH12Brake)
        {
            MuzzleLocalAxis=FVector::ForwardVector;
            MuzzleLocalTip=FVector(bASH12Brake?ASH12WeaponAssets::TacticalBrakeLengthCM:ASH12WeaponAssets::TacticalSuppressorLengthCM,0.f,0.f);
        }
        const auto& Ref=Rifle->GetRefSkeleton();
        auto Bone=[&](const TCHAR* Name){FTransform T=FTransform::Identity;for(int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE;I=Ref.GetParentIndex(I))T=T*Ref.GetRefBonePose()[I];return T;};
        const auto Root=Bone(TEXT("WPN_root")),Rear=Bone(TEXT("WPN_RearSight")),Front=Bone(TEXT("WPN_FrontSight")),Muzzle=Bone(TEXT("WPN_SOCKET_Muzzle"));
        const FVector Forward=bUseM16?Root.GetRotation().GetAxisY():(Front.GetLocation()-Rear.GetLocation()).GetSafeNormal();
        const FVector Up=bUseM16?Root.GetRotation().GetAxisZ():Rear.GetRotation().GetAxisZ();
        const FQuat SourceFrame=FRotationMatrix::MakeFromXZ(MuzzleLocalAxis,FVector::UpVector).ToQuat();
        const FQuat TargetFrame=FRotationMatrix::MakeFromXZ(Forward,Up).ToQuat();
        // Measured from the current export's factory flash-hider rear rim to its socket.
        const float BackOffset=bUseASH12?ASH12WeaponAssets::MuzzleBackOffset:4.83633f;
        // M16 attachments replace the factory hider at its actual rear bore
        // centre. Its legacy muzzle marker and sight line are both offset.
        const FVector MountLocation=bUseM16?Bone(M16WeaponAssets::MuzzleMountBone).GetLocation():Muzzle.GetLocation()-Forward*BackOffset;
        const FTransform Mount(TargetFrame*SourceFrame.Inverse(),MountLocation,FVector::OneVector);
        MuzzleAttachment->SetRelativeTransform(Mount.GetRelativeTransform(Root));
        if(!SuppressedFireSound)SuppressedFireSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed"));
    }
    MuzzleVariant=Desired;if(MuzzleAttachment)MuzzleAttachment->SetVisibility(!Desired.IsEmpty());
    if(const auto* Render=Rifle->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
    {
        const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
        if(Rifle->GetMaterials().IsValidIndex(M))
        {
            const FString Slot=Rifle->GetMaterials()[M].MaterialSlotName.ToString();
            const bool FactoryMuzzle=bUseM16?Slot==M16WeaponAssets::MuzzleMaterialSlot:Slot.Contains(TEXT("Flash_Hider"));
            if(FactoryMuzzle)AKMViewmodel->ShowMaterialSection(M,S,Desired.IsEmpty(),L);
        }
    }
}
FVector AFPSGAMECharacter::GetEffectiveMuzzleLocation() const
{
    if(bUseM16&&MuzzleVariant.IsEmpty())return AKMViewmodel->GetSocketTransform(M16WeaponAssets::MuzzleMountBone).TransformPosition(FVector(0.f,M16WeaponAssets::FactoryMuzzleLengthCM*.01f,0.f));
    if(AKMSoviet::Matches(AKMViewmodel)&&MuzzleVariant.IsEmpty())return AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).TransformPosition(AKMSoviet::Muzzle);
    return !MuzzleVariant.IsEmpty()&&MuzzleAttachment?MuzzleAttachment->GetComponentTransform().TransformPosition(MuzzleLocalTip):AKMViewmodel->GetSocketLocation(TEXT("WPN_SOCKET_Muzzle"));
}
FVector AFPSGAMECharacter::GetEffectiveMuzzleForward() const
{
    if(!MuzzleVariant.IsEmpty()&&MuzzleAttachment)return MuzzleAttachment->GetComponentQuat().RotateVector(MuzzleLocalAxis);
    if(bUseM16)return AKMViewmodel->GetSocketQuaternion(M16WeaponAssets::MuzzleMountBone).GetAxisY();
    if(IsPistolWeapon())return (AKMViewmodel->GetSocketLocation(TEXT("WPN_FrontSight"))-AKMViewmodel->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
    FVector F=AKMViewmodel->GetSocketQuaternion(TEXT("WPN_SOCKET_Muzzle")).GetAxisY();
    return FVector::DotProduct(F,FirstPersonCamera->GetForwardVector())<0?-F:F;
}
