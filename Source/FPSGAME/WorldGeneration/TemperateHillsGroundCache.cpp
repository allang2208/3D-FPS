#include "TemperateHillsWorld.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/RuntimeVirtualTextureComponent.h"
#include "VT/RuntimeVirtualTexture.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"

void ATemperateHillsWorld::ApplySmithYardGround()
{
    if (!VillageSite.bPlaced) return;
    if (GroundMID)
        GroundMID->SetScalarParameterValue(TEXT("SmithYardRepaired"), bVillageBlacksmithRepaired ? 1.f : 0.f);
    if (VillageSite.bSmithYardRepaired==bVillageBlacksmithRepaired) return;
    VillageSite.bSmithYardRepaired=bVillageBlacksmithRepaired;
    const FVector2D Center=VillageSite.World(-4080.,-900.);
    constexpr double Radius=760.;
    if(IsForestVillage() && !Terrain.IsEmpty()) BuildForestVillageGround();
    else InvalidateTerrainCells(Center,Radius);
    const FBoxSphereBounds Bounds(FBox::BuildAABB(FVector(Center,VillageSite.Ground.Z),FVector(Radius)));
    for (URuntimeVirtualTextureComponent* Cache : VillageGroundCache) if (Cache) Cache->Invalidate(Bounds);
}

void ATemperateHillsWorld::PrepareVillageGroundCache()
{
    if(!VillageSite.bPlaced||!Assets||VillageGroundCache.Num()||GetNetMode()==NM_DedicatedServer)return;
    if(!Assets->VillageColorCache.IsValid()||!Assets->VillageHeightCache.IsValid())return;
    if (!GroundMID) return;
    const FVector2D Extent=VillageSite.Extent()+FVector2D(6000.);
    const FVector Min=VillageSite.Ground-FVector(Extent,5000.);
    const FVector Size(Extent*2.,10000.);
    for(URuntimeVirtualTexture* Texture:{Assets->VillageColorCache.Get(),Assets->VillageHeightCache.Get()})
    {
        auto* C=NewObject<URuntimeVirtualTextureComponent>(this);
        AddInstanceComponent(C);C->SetMobility(EComponentMobility::Movable);
        // RVT's volume is the unit cube [0,1], not a centred box.
        C->SetWorldTransform(FTransform(FQuat::Identity,Min,Size));
        C->SetVirtualTexture(Texture);C->RegisterComponent();VillageGroundCache.Add(C);
    }
    for (UDynamicMeshComponent* Ground : Terrain) BindVillageGroundCache(Ground);
}

void ATemperateHillsWorld::ReleaseVillageGroundCache()
{
    for (URuntimeVirtualTextureComponent* Cache : VillageGroundCache)
    {
        if (Cache) { RemoveInstanceComponent(Cache); Cache->DestroyComponent(); }
    }
    VillageGroundCache.Reset();
}

void ATemperateHillsWorld::BindVillageGroundCache(UDynamicMeshComponent* Mesh)
{
    if(!Mesh||VillageGroundCache.IsEmpty())return;
    const FBox Box=Mesh->Bounds.GetBox();
    if(!VillageGroundCache[0]->Bounds.GetBox().Intersect(Box))return;
    Mesh->RuntimeVirtualTextures={Assets->VillageColorCache.Get(),Assets->VillageHeightCache.Get()};
    Mesh->VirtualTextureRenderPassType=ERuntimeVirtualTextureMainPassType::Always;
    Mesh->MarkRenderStateDirty();
}

void ATemperateHillsWorld::InvalidateVillageGroundCache(const UDynamicMeshComponent* Mesh)
{
    if(!Mesh||Mesh->RuntimeVirtualTextures.IsEmpty())return;
    for(const auto& Cache:VillageGroundCache)if(Cache)Cache->Invalidate(Mesh->Bounds);
}
