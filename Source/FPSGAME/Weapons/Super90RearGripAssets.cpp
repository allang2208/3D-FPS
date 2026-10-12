#include "Super90RearGripAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Rendering/SkeletalMeshRenderData.h"

UStaticMeshComponent* Super90RearGripAssets::Configure(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing,const FString& Variant,bool Enabled)
{
    if(Existing)Existing->SetVisibility(false);
    auto* Asset=Host?Host->GetSkeletalMeshAsset():nullptr;
    if(!Asset)return Existing;
    const auto& Ref=Asset->GetRefSkeleton();
    const int32 RootIndex=Ref.FindBoneIndex(TEXT("WPN_root"));
    const bool HasFactory=Asset->GetMaterials().ContainsByPredicate([](const FSkeletalMaterial& M)
        {return M.MaterialSlotName==TEXT("S90_FactoryRearGrip");});
    bool Installed=false;
    if(Enabled&&Supports(Variant)&&HasFactory&&RootIndex!=INDEX_NONE)
    {
        if(auto* Part=LoadObject<UStaticMesh>(nullptr,*MeshPath(Variant)))
        {
            if(!Existing)
            {
                Existing=NewObject<UStaticMeshComponent>(Owner);
                Owner->AddInstanceComponent(Existing);
                Existing->SetupAttachment(Host,TEXT("WPN_root"));
                Existing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                Existing->SetCastShadow(false);Existing->bReceivesDecals=false;
                Existing->RegisterComponent();
            }
            Existing->AttachToComponent(Host,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
            Existing->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
            Existing->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
            if(Existing->GetStaticMesh()!=Part)Existing->EmptyOverrideMaterials();
            Existing->SetStaticMesh(Part);
            FTransform Bind=FTransform::Identity;
            for(int32 I=RootIndex;I!=INDEX_NONE;I=Ref.GetParentIndex(I))Bind=Bind*Ref.GetRefBonePose()[I];
            // The fitted geometry is already in this skeletal mesh's bind space (cm).
            Existing->SetRelativeTransform(FTransform::Identity.GetRelativeTransform(Bind));
            Existing->SetVisibility(true);Installed=true;
        }
        else UE_LOG(LogTemp,Error,TEXT("Super90 missing rear grip %s"),*Variant);
    }
    if(const auto* Render=Asset->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(Asset->GetMaterials().IsValidIndex(M)&&Asset->GetMaterials()[M].MaterialSlotName==TEXT("S90_FactoryRearGrip"))
                    Host->ShowMaterialSection(M,S,!Installed,L);
            }
    return Existing;
}
