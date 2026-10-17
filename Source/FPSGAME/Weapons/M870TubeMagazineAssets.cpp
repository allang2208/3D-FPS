#include "M870TubeMagazineAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Rendering/SkeletalMeshRenderData.h"

UStaticMeshComponent* M870TubeMagazineAssets::Configure(AActor* Owner,USkeletalMeshComponent* Host,UStaticMeshComponent* Existing,bool Enabled)
{
    if(!Owner||!Host||!Host->GetSkeletalMeshAsset())return Existing;
    auto* Asset=Host->GetSkeletalMeshAsset();const auto& Ref=Asset->GetRefSkeleton();
    const int32 RootIndex=Ref.FindBoneIndex(TEXT("WPN_root"));
    const bool HasCap=Asset->GetMaterials().ContainsByPredicate([](const FSkeletalMaterial& M)
        {return M.MaterialSlotName.ToString().Equals(TEXT("M870_FactoryTubeCap"));});
    bool Installed=false;
    if(Enabled&&HasCap&&RootIndex!=INDEX_NONE)
        if(auto* PartMesh=LoadObject<UStaticMesh>(nullptr,MeshPath))
        {
            if(!Existing)
            {
                Existing=NewObject<UStaticMeshComponent>(Owner,TEXT("M870ExtendedTube"));Owner->AddInstanceComponent(Existing);
                Existing->SetupAttachment(Host,TEXT("WPN_root"));Existing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                Existing->SetCastShadow(false);Existing->bReceivesDecals=false;Existing->RegisterComponent();
            }
            Existing->AttachToComponent(Host,FAttachmentTransformRules::KeepRelativeTransform,TEXT("WPN_root"));
            Existing->SetOnlyOwnerSee(Host->bOnlyOwnerSee);Existing->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
            if(Existing->GetStaticMesh()!=PartMesh)Existing->EmptyOverrideMaterials();
            Existing->SetStaticMesh(PartMesh);
            FTransform Bind=FTransform::Identity;
            for(int32 I=RootIndex;I!=INDEX_NONE;I=Ref.GetParentIndex(I))Bind=Bind*Ref.GetRefBonePose()[I];
            Existing->SetRelativeTransform(FTransform::Identity.GetRelativeTransform(Bind));
            Existing->SetVisibility(true);Installed=true;
        }
    if(const auto* Render=Asset->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(Asset->GetMaterials().IsValidIndex(M)&&Asset->GetMaterials()[M].MaterialSlotName.ToString().Equals(TEXT("M870_FactoryTubeCap")))
                    Host->ShowMaterialSection(M,S,!Installed,L);
            }
    if(!Installed&&Existing){Existing->DestroyComponent();Existing=nullptr;}
    return Existing;
}
