#include "RSH12HeavyGrip.h"
#include "PistolGripSurface.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace RSH12HeavyGrip
{
void ShowFactory(USkeletalMeshComponent* Host,bool bVisible)
{
    const auto* Asset=Host?Host->GetSkeletalMeshAsset():nullptr;
    const auto* Render=Asset?Asset->GetResourceForRendering():nullptr;
    if(!Render)return;
    for(int32 L=0;L<Render->LODRenderData.Num();++L)
        for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        {
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            if(Asset->GetMaterials().IsValidIndex(M)&&Asset->GetMaterials()[M].MaterialSlotName==FactorySection)
                Host->ShowMaterialSection(M,S,bVisible,L);
        }
}
namespace
{
void Remove(TObjectPtr<UStaticMeshComponent>& Component)
{
    if(Component)Component->DestroyComponent();Component=nullptr;
}
void Fit(AActor* Owner,USkeletalMeshComponent* Host,TObjectPtr<UStaticMeshComponent>& Component,UStaticMesh* Mesh)
{
    if(!Component)
    {
        Component=NewObject<UStaticMeshComponent>(Owner);Owner->AddInstanceComponent(Component);
        Component->SetupAttachment(Host,TEXT("WPN_root"));
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);Component->SetCastShadow(false);
        Component->bReceivesDecals=false;Component->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
        Component->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);Component->RegisterComponent();
    }
    Component->EmptyOverrideMaterials();Component->SetStaticMesh(Mesh);
    const auto& Ref=Host->GetSkeletalMeshAsset()->GetRefSkeleton();FTransform Bind=FTransform::Identity;
    for(int32 I=Ref.FindBoneIndex(TEXT("WPN_root"));I!=INDEX_NONE;I=Ref.GetParentIndex(I))Bind=Bind*Ref.GetRefBonePose()[I];
    Component->SetRelativeTransform(FTransform::Identity.GetRelativeTransform(Bind));Component->SetVisibility(true);
}
}
void Configure(AActor* Owner,USkeletalMeshComponent* Host,
    TObjectPtr<UStaticMeshComponent>& Body,TObjectPtr<UStaticMeshComponent>& Surface,
    const FGunsmithWeapon* Weapon,const FString& BodyId,const FString& SurfaceId,bool bEnabled)
{
    const bool Replacement=bEnabled&&IsPart(BodyId)&&Host&&Host->GetSkeletalMeshAsset();
    if(!Replacement)
    {
        Remove(Body);ShowFactory(Host,true);
        Surface=PistolGripSurface::Configure(Owner,Host,Surface,Weapon,SurfaceId,bEnabled);return;
    }
    const bool QuickDraw=BodyId==QuickDrawPart;
    const FString Root=QuickDraw?TEXT("/Game/Weapons/RSH12/QuickDrawGrip20261005/"):TEXT("/Game/Weapons/RSH12/HeavyGrip20261005/");
    const FString Name=QuickDraw?TEXT("SM_RSH12_QuickDrawGrip"):TEXT("SM_RSH12_HeavyGrip");
    auto* BodyMesh=LoadObject<UStaticMesh>(nullptr,*(Root+TEXT("Meshes/")+Name));
    auto* SkinMesh=LoadObject<UStaticMesh>(nullptr,*(Root+TEXT("Meshes/")+Name+TEXT("_Surface")));
    if(!BodyMesh||!SkinMesh)
    {
        Remove(Body);ShowFactory(Host,true);
        Surface=PistolGripSurface::Configure(Owner,Host,Surface,Weapon,SurfaceId,bEnabled);return;
    }
    Fit(Owner,Host,Body,BodyMesh);Fit(Owner,Host,Surface,SkinMesh);
    // One fitted panel domain for all patterns, stopping above the metal heel.
    if(PistolGripSurface::IsPart(SurfaceId))
        if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*PistolGripSurface::MaterialPath(SurfaceId,Weapon)))Surface->SetMaterial(0,Material);
    ShowFactory(Host,false);
}
}
