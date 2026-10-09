#include "../FPSGAMECharacter.h"
#include "Super90OpticAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"

FTransform Super90OpticAssets::RailMount(const USkeletalMeshComponent* Host)
{
    const auto& Ref=Host->GetSkeletalMeshAsset()->GetRefSkeleton();
    FTransform Root=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Root=Root*Ref.GetRefBonePose()[I];
    // Measured native rail crown in component-space centimetres. Derive the
    // complete relative frame because the imported root's physical up is -Y.
    const FTransform Seat(FRotationMatrix::MakeFromXZ(FVector(0,-1,0),FVector::UpVector).ToQuat(),FVector(0,1.81334f,-71.813124f));
    return Seat.GetRelativeTransform(Root);
}
FTransform Super90OpticAssets::OpticMount(const USkeletalMeshComponent* Host,const FString& Variant)
{
    // The optic's own foot seats on the rail crown, without the former 6.5 mm
    // adapter. The original holographic foot is 0.03195 cm below its origin.
    FVector Offset=FVector::ZeroVector;
    if(Variant==TEXT("holographic"))Offset=FVector(2.260f,0,.03195f);
    else if(Variant==TEXT("lpvo_1_6x"))Offset.X=1.4f;
    else if(Variant==TEXT("eoth_holographic"))Offset.X=-2.6f;
    return FTransform(Offset)*RailMount(Host);
}
void Super90OpticAssets::FactorySights(USkeletalMeshComponent* Host,bool Visible)
{
    if(!Host||!Host->GetSkeletalMeshAsset())return;
    const auto* Mesh=Host->GetSkeletalMeshAsset();
    if(const auto* Render=Mesh->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(Mesh->GetMaterials().IsValidIndex(M)&&Mesh->GetMaterials()[M].MaterialSlotName==TEXT("FactorySights"))Host->ShowMaterialSection(M,S,Visible,L);
            }
}
void AFPSGAMECharacter::SetSuper90Optic(const FString& Variant)
{
    auto Remove=[](TObjectPtr<UStaticMeshComponent>& Part){if(Part){Part->DestroyComponent();Part=nullptr;}};
    const bool Enabled=bInventoryWeaponReady&&Super90OpticAssets::Supports(Variant);
    if(!Enabled)
    {
        Remove(LPVORing);Remove(HolographicOptic);Remove(AKMOpticBridge);
        Super90OpticAssets::FactorySights(AKMViewmodel,true);
        if(bHolographicOptic)bSightCalibrated=false;
        bHolographicOptic=false;OpticVariant.Reset();return;
    }
    if(!AKMViewmodel||!AKMViewmodel->GetSkeletalMeshAsset())return;
    Remove(AKMOpticBridge);
    const bool IsLPVO=Variant==TEXT("lpvo_1_6x");
    if(bHolographicOptic&&OpticVariant==Variant&&HolographicOptic&&(!IsLPVO||LPVORing))
    {
        HolographicOptic->SetVisibility(true);
        if(LPVORing)LPVORing->SetVisibility(IsLPVO);
        Super90OpticAssets::FactorySights(AKMViewmodel,false);return;
    }
    auto* Optic=LoadObject<UStaticMesh>(nullptr,*Super90OpticAssets::MeshPath(Variant));
    auto* Ring=IsLPVO?LoadObject<UStaticMesh>(nullptr,*Super90OpticAssets::MeshPath(TEXT("lpvo_ring"))):nullptr;
    if(!Optic||(IsLPVO&&!Ring)){UE_LOG(LogTemp,Error,TEXT("Super90 missing optic assembly %s"),*Variant);return;}
    auto Configure=[&](TObjectPtr<UStaticMeshComponent>& Part,UStaticMesh* PartMesh,USceneComponent* Parent,FName Socket,const FTransform& Local)
    {
        if(!Part)Part=NewObject<UStaticMeshComponent>(this);
        Part->EmptyOverrideMaterials();Part->SetStaticMesh(PartMesh);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->bReceivesDecals=false;
        Part->SetOnlyOwnerSee(AKMViewmodel->bOnlyOwnerSee);Part->SetFirstPersonPrimitiveType(AKMViewmodel->FirstPersonPrimitiveType);
        if(!Part->IsRegistered()){Part->SetupAttachment(Parent,Socket);Part->RegisterComponent();}
        else Part->AttachToComponent(Parent,FAttachmentTransformRules::KeepRelativeTransform,Socket);
        Part->SetRelativeTransform(Local);Part->SetVisibility(true);
    };
    HolographicMount=Super90OpticAssets::OpticMount(AKMViewmodel,Variant);
    Configure(HolographicOptic,Optic,AKMViewmodel,TEXT("WPN_root"),HolographicMount);
    if(OpticVariant!=Variant)LPVOMagnification=DisplayedLPVOMagnification=1.f;
    if(IsLPVO)Configure(LPVORing,Ring,HolographicOptic,TEXT("ZoomRing"),FTransform(FRotator(0,0,(DisplayedLPVOMagnification-1.f)*24.f)));
    else Remove(LPVORing);
    Super90OpticAssets::FactorySights(AKMViewmodel,false);
    OpticVariant=Variant;bHolographicOptic=true;bSightCalibrated=false;
}
