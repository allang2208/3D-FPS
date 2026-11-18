// Replace these two methods in the existing local AVillageDefenseGate implementation.
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void AVillageDefenseGate::PostNetInit()
{
    Super::PostNetInit();
    // Initial replicated state is a snapshot, not an opening animation. Apply
    // it to both visual and collision transforms before the first client tick.
    DisplayAngle=GateAngle;Pose(DisplayAngle);SetActorTickEnabled(false);
#if !UE_BUILD_SHIPPING
    if(FParse::Param(FCommandLine::Get(),TEXT("VillageNetworkAudit")))
        UE_LOG(LogTemp,Display,TEXT("VILLAGE_NET_GATE_INITIAL id=%d angle=%.2f left=%.2f right=%.2f"),
            SectionId,GateAngle,Masonry->GetRelativeRotation().Yaw,RightLeaf->GetRelativeRotation().Yaw);
#endif
}

void AVillageDefenseGate::PresentCollapse(const FVector& Direction,int32 Seed)
{
    for(auto* Leaf:{Masonry.Get(),RightLeaf.Get()})
    {
        // A destruction RPC can arrive between the two asynchronous mesh loads.
        // Missing cosmetic geometry must never prevent authoritative destruction.
        const UStaticMesh* Mesh=Leaf->GetStaticMesh();
        if(!Mesh)continue;
        const FVector Size=Mesh->GetBoundingBox().GetSize();
        FTransform T=Leaf->GetComponentTransform();
        FVector Center=Mesh->GetBoundingBox().GetCenter();Center.Z=0.;
        T.SetLocation(T.TransformPosition(Center));
        AVillageDefenseDebris::Spawn(GetWorld(),T,Size,Direction,Seed++,true);
    }
}
