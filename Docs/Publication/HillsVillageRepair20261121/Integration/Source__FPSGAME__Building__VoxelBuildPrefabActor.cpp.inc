// Source/FPSGAME/Building/VoxelBuildPrefabActor.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 2-3 | file scope
#include "VoxelBuildWorld.h"
#include "VillageBuildDefense.h"

// Lines 18-20 | AVoxelBuildPrefabActor::AVoxelBuildPrefabActor()
    // The wrapper carries its attached building. Byte precision merges neighbouring 1-degree turns.
    GetReplicatedMovement_Mutable().RotationQuantizationLevel=ERotatorQuantization::ShortComponents;
    GetReplicatedMovement_Mutable().LocationQuantizationLevel=EVectorQuantization::RoundTwoDecimals;

// Lines 53-67 | void AVoxelBuildPrefabActor::OnRep_Owner()
void AVoxelBuildPrefabActor::OnRep_Owner()
{
    Super::OnRep_Owner();
    if(auto* Building=Cast<AVoxelBuildWorld>(GetOwner()))Building->RefreshReplicatedVillagePiece(*this);
}

void AVoxelBuildPrefabActor::OnRep_Configuration()
{
    // The attached masonry inherits its carrier's scale; spawn quantization rounds 1.25 to 1.3.
    if(Id==VillageBuildDefense::StoneWall)SetActorScale3D(VillageBuildDefense::PlacementScale(Id));
    // A reset scene station still has its authored body, but its tool rack or
    // spinning saw must be detached on clients when the replicated id clears.
    if(!Id.IsNone()||NetMesh)Configure(Id,Cell,QuarterTurns,NetMesh,NetSurface,nullptr);
    OnRep_Falling();
}

// Lines 155-155 | void AVoxelBuildPrefabActor::OnRep_Falling()
    if(auto* Building=Cast<AVoxelBuildWorld>(GetOwner()))Building->RefreshReplicatedVillagePiece(*this);
