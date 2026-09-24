#include "ColdSteelPickup.h"
#include "Engine/World.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "../Production/ProductionHarvestAssets.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "EngineUtils.h"

bool AColdSteelPickup::BuildProductionMaterial(const FColdSteelItem& Item)
{
    if(!ProductionHarvestAssets::IsMaterial(Item.Definition))return false;
    bProductionMaterial=true;SetActorTickInterval(.15f);
    Body->SetSimulatePhysics(false);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetStaticMesh(nullptr);
    const bool Wood=Item.Definition==TEXT("wood");
    const auto Path=ProductionHarvestAssets::PickupMesh(Item.Definition,GetTypeHash(Item.InstanceId)%3);
    const auto MatPath=ProductionHarvestAssets::PickupMaterial(Item.Definition);   // 矿石/金属锭的分种材质（2026-09-24 建模接入）
    if(auto* Asset=Cast<UStaticMesh>(Path.ResolveObject()))InstallProductionMaterial(Asset,Wood,Item.Definition);
    else
    {   TArray<FSoftObjectPath> Wants={Path};if(MatPath.IsValid())Wants.Add(MatPath);   // 网格与材质一次批量预载
        ProductionToolLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Wants,
            FStreamableDelegate::CreateWeakLambda(this,[this,Path,Wood,Def=Item.Definition]()
            {if(auto* Asset=Cast<UStaticMesh>(Path.ResolveObject()))InstallProductionMaterial(Asset,Wood,Def);}));   }
    return true;
}
void AColdSteelPickup::InstallProductionMaterial(UStaticMesh* Asset,bool Wood,const FString& Definition)
{
    const auto Bounds=Asset->GetBounds();
    // Authored timber variants already carry their real 73-80 cm dimensions.
    const float Scale=Wood?1.f:24.f/FMath::Max(1.f,2.f*float(Bounds.BoxExtent.GetMax()));
    Mesh->SetStaticMesh(Asset);Mesh->SetRelativeScale3D(FVector(Scale));Mesh->SetRelativeLocation(-Bounds.Origin*Scale);
    if(const auto MPath=ProductionHarvestAssets::PickupMaterial(Definition);MPath.IsValid())
        if(auto* Mat=Cast<UMaterialInterface>(MPath.ResolveObject()))Mesh->SetMaterial(0,Mat);   // 已随网格一并预载
    Body->SetBoxExtent((Bounds.BoxExtent*Scale).ComponentMax(FVector(3)));
    Body->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Body->SetCollisionResponseToChannel(ECC_PhysicsBody,ECR_Ignore);
    const FVector Size=Bounds.BoxExtent*(2*Scale);
    ProductionMassKg=Wood?FMath::Clamp(float(Size.X*Size.Y*Size.Z)*.000001f*.7854f*550.f,4.f,40.f):.8f;
    Body->SetLinearDamping(Wood?.7f:1.8f);Body->SetAngularDamping(Wood?1.2f:4.f);
    Body->SetSimulatePhysics(true);
    if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Fluid->RegisterWaterBody(Body);
    Body->SetMassOverrideInKg(NAME_None,ProductionMassKg);
    // Older saves contain narrow branch-sized drops; lift a wider replacement out of the ground.
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
    {
        FVector At=GetActorLocation();const float Floor=It->Height(At.X,At.Y)+Body->Bounds.BoxExtent.Z+2;
        if(At.Z<Floor){At.Z=Floor;SetActorLocation(At,false,nullptr,ETeleportType::TeleportPhysics);}break;
    }
    bProductionMaterialReady=true;ProductionSettleSeconds=6.f;ProductionQuietSeconds=0;
}
void AColdSteelPickup::TickProductionMaterial(float Delta)
{
    if(!bProductionMaterialReady||ProductionSettleSeconds<=0)return;
    ProductionSettleSeconds-=Delta;
    const bool Quiet=Body->GetPhysicsLinearVelocity().SizeSquared()<9.f&&Body->GetPhysicsAngularVelocityInDegrees().SizeSquared()<36.f;
    ProductionQuietSeconds=Quiet?ProductionQuietSeconds+Delta:0;
    if(ProductionSettleSeconds>0&&ProductionQuietSeconds<.6f)return;
    ProductionSettleSeconds=0;
    Body->SetPhysicsLinearVelocity(FVector::ZeroVector);Body->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
    Body->SetSimulatePhysics(false);Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    // If terrain collision was streaming during the release, restore to its analytic surface.
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
    {
        FVector At=GetActorLocation();const float Ground=It->Height(At.X,At.Y);
        if(At.Z<Ground-5){At.Z=Ground+Body->Bounds.BoxExtent.Z+2;SetActorLocation(At);}break;
    }
}
