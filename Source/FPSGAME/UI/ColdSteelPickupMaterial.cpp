#include "ColdSteelPickup.h"
#include "../Production/ProductionHarvestAssets.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "EngineUtils.h"

bool AColdSteelPickup::BuildProductionMaterial(const FColdSteelItem& Item)
{
    if(!ProductionHarvestAssets::IsMaterial(Item.Definition))return false;
    bProductionMaterial=true;SetActorTickInterval(.15f);
    Body->SetSimulatePhysics(false);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetStaticMesh(nullptr);
    const bool Wood=Item.Definition==TEXT("wood");const auto Path=ProductionHarvestAssets::PickupMesh(Item.Definition);
    if(auto* Asset=Cast<UStaticMesh>(Path.ResolveObject()))InstallProductionMaterial(Asset,Wood);
    else ProductionToolLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Path,
        FStreamableDelegate::CreateWeakLambda(this,[this,Path,Wood]()
        {if(auto* Asset=Cast<UStaticMesh>(Path.ResolveObject()))InstallProductionMaterial(Asset,Wood);}));
    return true;
}
void AColdSteelPickup::InstallProductionMaterial(UStaticMesh* Asset,bool Wood)
{
    const auto Bounds=Asset->GetBounds();
    const float Scale=(Wood?85.f:24.f)/FMath::Max(1.f,2.f*float(Bounds.BoxExtent.GetMax()));
    Mesh->SetStaticMesh(Asset);Mesh->SetRelativeScale3D(FVector(Scale));Mesh->SetRelativeLocation(-Bounds.Origin*Scale);
    Body->SetBoxExtent((Bounds.BoxExtent*Scale).ComponentMax(FVector(3)));
    Body->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Body->SetCollisionResponseToChannel(ECC_PhysicsBody,ECR_Ignore);
    Body->SetLinearDamping(1.8f);Body->SetAngularDamping(4.f);Body->SetSimulatePhysics(true);Body->SetMassOverrideInKg(NAME_None,Wood?1.2f:.8f);
    bProductionMaterialReady=true;ProductionSettleSeconds=2.f;
}
void AColdSteelPickup::TickProductionMaterial(float Delta)
{
    if(!bProductionMaterialReady||ProductionSettleSeconds<=0)return;
    ProductionSettleSeconds-=Delta;if(ProductionSettleSeconds>0)return;
    Body->SetPhysicsLinearVelocity(FVector::ZeroVector);Body->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
    Body->SetSimulatePhysics(false);Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    // If terrain collision was streaming during the release, restore to its analytic surface.
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
    {
        FVector At=GetActorLocation();const float Ground=It->Height(At.X,At.Y);
        if(At.Z<Ground-5){At.Z=Ground+Body->Bounds.BoxExtent.Z+2;SetActorLocation(At);}break;
    }
}
