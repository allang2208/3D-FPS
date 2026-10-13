#include "WoodworkingSawVisualComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"

namespace
{
const FSoftObjectPath WoodworkingEdgePaintPath(TEXT("/Game/Building/WoodworkingBenchV6Controls20261013/Materials/M_SawEdgePaint.M_SawEdgePaint"));
}

UWoodworkingSawVisualComponent::UWoodworkingSawVisualComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickInterval=1.f/60.f;
    BodyAsset=TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Building/WoodworkingBenchV6Controls20261013/SM_WoodworkingBenchBody.SM_WoodworkingBenchBody")));
    BladeAsset=TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Building/WoodworkingBenchV6Controls20261013/SM_WoodworkingSawBlade.SM_WoodworkingSawBlade")));
}

void UWoodworkingSawVisualComponent::Configure(UStaticMeshComponent* Station)
{
    if(!Station||AssetLoad||!Station->DoesSocketExist(TEXT("WoodworkingSawPivot"))
        ||!GetWorld()||!GetWorld()->IsGameWorld()||GetNetMode()==NM_DedicatedServer)return;
    Body=Station;OriginalMesh=Station->GetStaticMesh();
    TArray<FSoftObjectPath> Paths={BodyAsset.ToSoftObjectPath(),BladeAsset.ToSoftObjectPath(),WoodworkingEdgePaintPath};
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateUObject(this,&UWoodworkingSawVisualComponent::AssetsReady));
}

void UWoodworkingSawVisualComponent::AssetsReady()
{
    auto* Station=Body.Get();
    if(!Station||Station->IsSimulatingPhysics()||Station->GetStaticMesh()!=OriginalMesh
        ||!BodyAsset.Get()||!BladeAsset.Get()||!BodyAsset.Get()->FindSocket(TEXT("WoodworkingSawPivot")))return;
    // The preview and body preserve the original material-slot order and placement bounds.
    // Keep existing per-instance material overrides when replacing the preview mesh.
    Blade=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
    GetOwner()->AddInstanceComponent(Blade);
    Blade->SetMobility(EComponentMobility::Movable);
    Blade->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Blade->SetGenerateOverlapEvents(false);
    Blade->SetCanEverAffectNavigation(false);
    Blade->SetStaticMesh(BladeAsset.Get());
    // All LOD sections of the separate blade use its local radial paint mask.
    // This also covers a section still mapped to the original atlas material.
    if(auto* Paint=Cast<UMaterialInterface>(WoodworkingEdgePaintPath.ResolveObject()))
        for(int32 Slot=0;Slot<Blade->GetNumMaterials();++Slot)Blade->SetMaterial(Slot,Paint);
    Blade->SetupAttachment(Station,TEXT("WoodworkingSawPivot"));
    Blade->SetRelativeTransform(FTransform::Identity);
    Blade->SetRelativeLocation(bAdjusting?FVector(0,0,-12):FVector::ZeroVector);
    Station->SetStaticMesh(BodyAsset.Get());
    Blade->RegisterComponent();
    SetComponentTickEnabled(bPowered);
}

void UWoodworkingSawVisualComponent::SetPowered(bool bInPowered,bool Adjusting)
{
    auto* Station=Body.Get();
    const bool bNextAdjusting=Adjusting&&Station&&!Station->IsSimulatingPhysics();
    if(bAdjusting!=bNextAdjusting)
    {
        bAdjusting=bNextAdjusting;
        // V6 blade top becomes 93 cm, below the tabletop and the 95.65 cm stock bottom.
        if(IsValid(Blade))Blade->SetRelativeLocation(bAdjusting?FVector(0,0,-12):FVector::ZeroVector);
    }
    const bool bNext=bInPowered&&!bAdjusting&&Station&&!Station->IsSimulatingPhysics();
    if(bPowered==bNext)return;
    bPowered=bNext;SetComponentTickEnabled(bPowered&&IsValid(Blade));
}

void UWoodworkingSawVisualComponent::TickComponent(float Delta,ELevelTick TickType,FActorComponentTickFunction* ThisTick)
{
    Super::TickComponent(Delta,TickType,ThisTick);
    auto* Station=Body.Get();
    if(!bPowered||!Station||Station->IsSimulatingPhysics()||!IsValid(Blade))
    {SetPowered(false);SetComponentTickEnabled(false);return;}
    // Cosmetic speed only. Fixed local X and the imported socket follow every placed yaw.
    Angle=FMath::Fmod(Angle+double(FMath::Clamp(Delta,0.f,.1f))*720.,360.);
    Blade->SetRelativeRotation(FQuat(FVector::XAxisVector,FMath::DegreesToRadians(Angle)));
}

void UWoodworkingSawVisualComponent::OnComponentDestroyed(bool bDestroyingHierarchy)
{
    SetPowered(false);
    if(AssetLoad)AssetLoad->CancelHandle();
    if(IsValid(Blade))Blade->DestroyComponent();
    Blade=nullptr;
    if(auto* Station=Body.Get();Station&&OriginalMesh&&Station->GetStaticMesh()==BodyAsset.Get())Station->SetStaticMesh(OriginalMesh);
    AssetLoad.Reset();Body.Reset();OriginalMesh=nullptr;
    Super::OnComponentDestroyed(bDestroyingHierarchy);
}
