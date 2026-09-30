#include "FluidPresentationSubsystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Production/ProductionHarvestAssets.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"
#include "Materials/MaterialInterface.h"

void UFluidPresentationSubsystem::ReleaseCastingRack(FFurnaceSmoke& Entry)
{
    for(int32 Lane=0;Lane<4;++Lane)
    {
        if(auto* Rack=Entry.Rack[Lane].Get())
        {
            Rack->ClearInstances();Rack->SetVisibility(false);
            Rack->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
        }
        Entry.Rack[Lane].Reset();Entry.RackCounts[Lane]=-1;
    }
    Entry.RackParent.Reset();
}

void UFluidPresentationSubsystem::UpdateCastingRack(FFurnaceSmoke& Entry,AVoxelBuildWorld* Build,const FVoxelSmeltingJob* Job)
{
    auto* Station=Build&&Job&&Job->bCasting?Build->PrefabActorAt(Job->StationCell):nullptr;
    auto* Body=Station?Station->Body():nullptr;
    if(!Body||!Body->IsRegistered()||Station->IsFalling()||Station->PrefabId()!=VoxelCastingStationId
        ||!bHasView||FVector::DistSquared(Body->GetComponentLocation(),Eye)>FMath::Square(8500.f))
    {ReleaseCastingRack(Entry);return;}
    if(Entry.RackParent.Get()!=Body){ReleaseCastingRack(Entry);Entry.RackParent=Body;}
    auto* Mesh=Cast<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Items/Smelting/Ingot/SM_Ingot.SM_Ingot")).ResolveObject());
    if(!Mesh)return;
    static const FString Metals[]={TEXT("ironIngot"),TEXT("copperIngot"),TEXT("silverIngot"),TEXT("goldIngot")};
    for(int32 Lane=0;Lane<4;++Lane)
    {
        const auto* Product=Job->Products.FindByPredicate([&](const auto& P){return P.Item==Metals[Lane];});
        // Three physical examples per lane; the saved/UI count owns all 60 storage positions.
        const int32 Count=Product?int32(FMath::Clamp<int64>(Product->Count,0,3)):0;
        if(Entry.RackCounts[Lane]==Count)continue;
        auto* Rack=Entry.Rack[Lane].Get();
        if(!Rack&&Count>0)
        {
            auto* Material=Cast<UMaterialInterface>(ProductionHarvestAssets::PickupMaterial(Metals[Lane]).ResolveObject());
            if(!Material)continue;
            for(auto& Candidate:CastingRackPool)
            {
                if(!IsValid(Candidate))continue;
                bool Taken=false;
                for(const auto& Other:Furnaces)
                    for(const auto& Borrowed:Other.Rack)if(Borrowed.Get()==Candidate.Get())Taken=true;
                if(!Taken){Rack=Candidate.Get();break;}
            }
            if(!Rack&&CastingRackPool.Num()<32*4)
            {
                auto* RackOwner=GetWorld()->GetWorldSettings();
                Rack=NewObject<UInstancedStaticMeshComponent>(RackOwner,NAME_None,RF_Transient);
                RackOwner->AddInstanceComponent(Rack);
                Rack->SetMobility(EComponentMobility::Movable);
                Rack->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                Rack->SetGenerateOverlapEvents(false);Rack->SetCanEverAffectNavigation(false);
                Rack->SetCastShadow(false);Rack->SetCullDistances(7500,8500);
                Rack->RegisterComponent();CastingRackPool.Add(Rack);
            }
            if(!Rack)continue;
            Rack->SetStaticMesh(Mesh);Rack->SetMaterial(0,Material);
            Rack->AttachToComponent(Body,FAttachmentTransformRules::SnapToTargetIncludingScale);
            Rack->SetRelativeTransform(FTransform::Identity);Entry.Rack[Lane]=Rack;
        }
        if(Rack)
        {
            Rack->ClearInstances();
            const auto Bounds=Mesh->GetBounds();
            const float Scale=20.f/FMath::Max(1.f,2.f*float(FMath::Max(Bounds.BoxExtent.X,Bounds.BoxExtent.Y)));
            // Long axis across the lane; all positions are authored station mesh space in cm.
            const FRotator Rotation(0,Bounds.BoxExtent.Y>Bounds.BoxExtent.X?0.f:90.f,0);
            const FVector CentreOffset=Rotation.RotateVector(Bounds.Origin*Scale);
            for(int32 Index=0;Index<Count;++Index)
            {
                const FVector Centre(-72.f+15.f*Index,-36.75f+24.5f*Lane,34.2f+Bounds.BoxExtent.Z*Scale);
                Rack->AddInstance(FTransform(Rotation,Centre-CentreOffset,FVector(Scale)),false);
            }
            Rack->SetVisibility(Count>0);
        }
        Entry.RackCounts[Lane]=Count;
    }
}
