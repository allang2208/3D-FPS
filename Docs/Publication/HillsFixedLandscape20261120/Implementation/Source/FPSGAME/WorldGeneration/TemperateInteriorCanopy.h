#pragma once

#include "TemperateHillsSurface.h"
#include "TemperateHillsVisibility.h"
#include "TemperateHillsWorld.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"

namespace TemperateBackdrop
{
// Interior silhouettes reuse a sparse subset of the actual 12 m tree lattice.
// Each quadrant of a quadrant owns one instanced component, so bounds stay local.
struct FInteriorCanopy
{
    static constexpr int32 Sectors=16;
    static int32 CrownLimitPerSector(int32 TotalBudget){return FMath::Clamp(TotalBudget/(3*Sectors),0,32);}
    struct FCrown
    {
        uint64 Id;
        FTransform Pose;
        TWeakObjectPtr<UInstancedStaticMeshComponent> Component;
        int32 Instance;
        bool Hidden;
    };
    struct FPendingCrown {uint64 Id; FTransform Pose;};
    TArray<TWeakObjectPtr<UStaticMesh>> Forms;
    TArray<TWeakObjectPtr<UInstancedStaticMeshComponent>> Components;
    TArray<FCrown> Crowns;
    TArray<FPendingCrown> Pending;
    int32 Sector=0,Tile=0,RefreshIndex=0;
    uint32 HeightRevision=0;
    double NextHarvestRefresh=0;
    bool Initialized=false;

    void Tick(const ATemperateHillsWorld& Hills,AActor& Owner,
        TFunctionRef<bool(int32,int32,FTemperatePlacement&)> Tree)
    {
        // Terrain edits can move a root or invalidate its entire planting site.
        if(Initialized&&HeightRevision!=Hills.GetTerrainEditRevision())
        {
            for(const auto& Ref:Components)if(auto* Part=Ref.Get())Part->DestroyComponent();
            *this=FInteriorCanopy{};
        }
        if(!Initialized)
        {
            for(const auto& Ref:Hills.Assets->BackdropTrees)
                if(Ref.ToSoftObjectPath().GetAssetName().StartsWith(TEXT("SM_HillsAlderCrown_"))&&Ref.IsValid())
                    Forms.Add(Ref.Get());
            HeightRevision=Hills.GetTerrainEditRevision();
            Initialized=true;
        }
        if(Forms.IsEmpty())return;

        // Harvest changes near a different player can also affect this horizon.
        // Keep the same ID as PCG and leave regrowing trees to their growth actor.
        const double Now=FPlatformTime::Seconds();
        const int32 Checks=Now>=NextHarvestRefresh?FMath::Min(8,Crowns.Num()):0;
        if(Checks)NextHarvestRefresh=Now+.04;
        for(int32 I=0;I<Checks;++I)
        {
            if(RefreshIndex>=Crowns.Num())RefreshIndex=0;
            FCrown& Crown=Crowns[RefreshIndex++];
            const bool Hidden=Hills.IsProductionDepleted(0,Crown.Id);
            if(Hidden==Crown.Hidden)continue;
            if(auto* Part=Crown.Component.Get())
            {
                FTransform Pose=Crown.Pose;
                if(Hidden)Pose.SetScale3D(FVector::ZeroVector);
                Part->UpdateInstanceTransform(Crown.Instance,Pose,false,true,true);
            }
            Crown.Hidden=Hidden;
        }
        constexpr int32 TilesPerSide=11,TilesPerSector=TilesPerSide*TilesPerSide;
        const int32 Limit=CrownLimitPerSector(Hills.Assets->BackdropTreeBudget);
        if(Sector>=Sectors||Limit==0)return;

        // Across the fixed 1024 m map, rotate the order of sectors and candidates.
        // A busy frame visits only a handful of real tree sites, after entry.
        const int32 SectorId=(Sector*7+5)%Sectors;
        UStaticMesh* Form=Forms[TemperateHillsSurface::Mix(SectorId+91)%Forms.Num()].Get();
        if(!Form)return;
        const double Deadline=FPlatformTime::Seconds()+.00030;
        for(int32 Step=0;Step<12&&Tile<TilesPerSector&&Pending.Num()<Limit;++Step)
        {
            const int32 Index=(Tile++*47+SectorId*13)%TilesPerSector;
            const int32 X=(SectorId%4)*TilesPerSide+Index%TilesPerSide-22;
            const int32 Y=(SectorId/4)*TilesPerSide+Index/TilesPerSide-22;
            const uint32 Key=TemperateHillsSurface::Key(X,Y,Hills.Seed,4793);
            FTemperatePlacement Site;
            if(Tree(X*2+int32(Key&1),Y*2+int32((Key>>1)&1),Site))
            {
                if(const auto* Skin=Cast<USkeletalMesh>(Site.Mesh.ResolveObject()))
                {
                    const FBox Source=Skin->GetImportedBounds().GetBox();
                    const FBox Target=Form->GetBoundingBox();
                    const FVector Size=Source.GetSize()*Site.Transform.GetScale3D();
                    // Camera-facing donor cards have a thin original mesh axis.
                    // Apply a uniform horizontal scale from the full donor bounds.
                    const double Width=FMath::Max(Target.GetSize().X,Target.GetSize().Y);
                    const double XY=FMath::Max(Size.X,Size.Y)/FMath::Max(1.,Width);
                    FTransform Pose=Site.Transform;
                    Pose.SetScale3D(FVector(XY,XY,Size.Z/FMath::Max(1.,Target.GetSize().Z)));
                    Pending.Add({Site.CandidateId,Pose});
                }
            }
            if(FPlatformTime::Seconds()>=Deadline)break;
        }
        if(Tile<TilesPerSector&&Pending.Num()<Limit)return;
        if(!Pending.IsEmpty())
        {
            auto* Part=NewObject<UInstancedStaticMeshComponent>(&Owner);
            Owner.AddInstanceComponent(Part);
            Part->SetupAttachment(Owner.GetRootComponent());
            Part->SetMobility(EComponentMobility::Movable);
            Part->SetStaticMesh(Form);
            // ISM exposes a per-instance minimum distance. A component minimum
            // would hide the entire copse when approaching only its nearest edge.
            Part->InstanceMinDrawDistance=int32(TemperateHillsVisibility::Layers[0].VisibleEnd);
            Part->SetCullDistances(0,155000);
            Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Part->SetCanEverAffectNavigation(false);
            Part->SetGenerateOverlapEvents(false);
            Part->SetCastShadow(false);
            Part->bAffectDistanceFieldLighting=false;
            Part->bVisibleInRayTracing=false;
            for(const auto& Site:Pending)
            {
                const bool Hidden=Hills.IsProductionDepleted(0,Site.Id);
                FTransform Pose=Site.Pose;
                if(Hidden)Pose.SetScale3D(FVector::ZeroVector);
                const int32 Instance=Part->AddInstance(Pose);
                Crowns.Add({Site.Id,Site.Pose,Part,Instance,Hidden});
            }
            Part->RegisterComponent();
            Components.Add(Part);
            Pending.Reset();
        }
        ++Sector;
        Tile=0;
    }
};
}
