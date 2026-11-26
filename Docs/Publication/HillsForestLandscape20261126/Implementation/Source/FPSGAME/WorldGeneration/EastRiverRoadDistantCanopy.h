#pragma once
#include "EastRiverRoad.h"
#include "TemperateHillsWorld.h"
#include "TemperateHillsVisibility.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Animation/AnimBank.h"
#include "Engine/SkeletalMesh.h"

// Continue the two reference forms beyond the tree PCG cell draw range.
struct FEastRiverRoadDistantCanopy
{
    struct FSite { uint64 Key; FTransform Pose; int32 Form; FPrimitiveInstanceId Instance; bool Hidden; };
    TWeakObjectPtr<UInstancedSkinnedMeshComponent> Parts[2];
    TArray<FIntPoint> Cells;
    TArray<FSite> Sites;
    int32 NextCell=0,NextSite=0;
    uint32 Revision=MAX_uint32;
    double NextRefresh=0.;
    void Tick(const ATemperateHillsWorld& Hills,AActor& Host,TFunctionRef<bool(int32,int32,FTemperatePlacement&)> Tree)
    {
        if(!EastRiverRoad::Enabled(Hills.Seed,Hills.GeneratorVersion,Hills.GetVillageSite()))return;
        if(Revision!=Hills.GetTerrainEditRevision())
        {
            for(auto& Ref:Parts){if(auto* Part=Ref.Get())Part->DestroyComponent();Ref.Reset();}
            Cells=EastRiverRoad::ForestTiles();
            Sites.Reset();NextCell=NextSite=0;Revision=Hills.GetTerrainEditRevision();
        }
        if(NextCell<Cells.Num())
        {
            const auto Cell=Cells[NextCell++];
            for(auto Address:EastRiverRoad::TreeKeys(Hills,Cell.X,Cell.Y))
            {
                FTemperatePlacement P;
                if(!Tree(Address.X,Address.Y,P))continue;
                const int32 Form=EastRiverRoad::CanopyForm(P.Mesh);
                if(Form==INDEX_NONE)continue;
                auto* Part=Parts[Form].Get();
                if(!Part)
                {
                    Part=NewObject<UInstancedSkinnedMeshComponent>(&Host);
                    Host.AddInstanceComponent(Part);Part->SetupAttachment(Host.GetRootComponent());
                    FSkinnedMeshComponentDescriptor DrawRange;
                    DrawRange.InitFrom(Part,false);
                    DrawRange.InstanceMinDrawDistance=int32(TemperateHillsVisibility::Layers[0].VisibleEnd);
                    DrawRange.InstanceEndCullDistance=155000;
                    DrawRange.InitComponent(Part);
                    Part->SetSkinnedAsset(CastChecked<USkeletalMesh>(P.Mesh.ResolveObject()));
                    Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCanEverAffectNavigation(false);
                    Part->SetCastShadow(false);Part->bVisibleInRayTracing=false;
                    Part->RegisterComponent();Parts[Form]=Part;
                }
                const bool Hidden=Hills.IsProductionDepleted(0,P.CandidateId);
                FTransform Draw=P.Transform;if(Hidden)Draw.SetScale3D(FVector::ZeroVector);
                const auto Instance=Part->AddInstance(Draw,0,true);
                Sites.Add({P.CandidateId,P.Transform,Form,Instance,Hidden});
            }
        }
        const double Now=FPlatformTime::Seconds();
        if(Sites.IsEmpty()||Now<NextRefresh)return;
        NextRefresh=Now+.05;
        for(int32 I=0;I<FMath::Min(16,Sites.Num());++I)
        {
            FSite& Site=Sites[NextSite];NextSite=(NextSite+1)%Sites.Num();
            const bool Hidden=Hills.IsProductionDepleted(0,Site.Key);
            if(Hidden==Site.Hidden)continue;
            FTransform Draw=Site.Pose;if(Hidden)Draw.SetScale3D(FVector::ZeroVector);
            if(auto* Part=Parts[Site.Form].Get())Part->SetInstanceTransform(Site.Instance,Draw,true);
            Site.Hidden=Hidden;
        }
    }
};
