#include "VoxelBuildWorld.h"
#include "VoxelBuildGrounding.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelSupportGraph.h"
#include "VillageBuildDefense.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"

void AVoxelBuildWorld::RefreshReplicatedVillagePiece(AVoxelBuildPrefabActor& Piece)
{
    if(HasAuthority()||Piece.GetOwner()!=this||!VillageBuildDefense::IsVillageRecipe(Piece.PrefabId()))return;
    const FIntVector Cell=Piece.AnchorCell();
    if(!Piece.IsFalling())PrefabActors.Add(Cell,&Piece);
    else if(PrefabActors.FindRef(Cell).Get()==&Piece)PrefabActors.Remove(Cell);
    // Snapshot data, the carrier and its attached defense can arrive in different packets.
    CachedGridRecipe=NAME_None;
    if(!Piece.IsFalling())
        if(const auto* Section=Cast<AVillageDefenseSection>(Piece.Logic()))OnVillageSupportChanged(*Section);
}

bool AVoxelBuildWorld::CanBearLoadAt(FIntVector Anchor,FIntVector Cell) const
{
    const auto* Piece=Cast<AVoxelBuildPrefabActor>(PrefabActors.FindRef(Anchor).Get());
    if(!Piece||Piece->IsFalling())return false;
    const FName Id=Piece->PrefabId();
    if(!VillageBuildDefense::IsVillageRecipe(Id))return true;
    const auto* Section=Cast<AVillageDefenseSection>(Piece->Logic());
    if(!IsValid(Section))return false;
    if(Id!=VillageBuildDefense::StoneGate&&Id!=VillageBuildDefense::WoodGate)
        return Section->GetHealth()>0.f;

    // Only fixed stonework bears weight. The closed leaf, even when visible, and
    // the reserved travel channel must never give a neighbouring voxel a foundation.
    const FVector Center=CellCenter(Cell);
    const FCollisionShape Box=FCollisionShape::MakeBox(FVector(CellSizeCm*.5-.01));
    TInlineComponentArray<UStaticMeshComponent*> Parts(Section);
    for(const UStaticMeshComponent* Part:Parts)
        if(Part->ComponentHasTag(TEXT("Traversal.FixedStructure"))&&Part->IsQueryCollisionEnabled()&&
            Part->Bounds.GetBox().ExpandBy(CellSizeCm*.5).IsInsideOrOn(Center)&&
            Part->OverlapComponent(Center,FQuat::Identity,Box))return true;
    return false;
}

bool AVoxelBuildWorld::FindWallBacking(const FVoxelBuildPrefabInstance& Piece,FHitResult& Surface) const
{
    const bool bAlongX=(Piece.Yaw&1)==0;
    FVector Axis=FVector::ZeroVector;
    Axis[bAlongX?0:1]=(Piece.Yaw&2)?-1.:1.;
    const FVector Center=CellMin(Piece.Cell)+FVector(Piece.Footprint)*10.;
    const double Depth=(bAlongX?Piece.Footprint.X:Piece.Footprint.Y)*10.;
    const FVector Back=Center-Axis*Depth;
    // The stored grid face may have rounded into the wall. Probe it from outside.
    const FVector Span=Axis*(CellSizeCm+1.);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(PrefabWallVerify),true);
    if(const auto* Self=Cast<AVoxelBuildPrefabActor>(PrefabActors.FindRef(Piece.Cell).Get()))
    {
        Params=VoxelGrounding::Query(GetWorld(),Self);
        Params.AddIgnoredActor(Self->Logic());
    }
    if(!GetWorld()->LineTraceSingleByChannel(Surface,Back+Span,Back-Span,ECC_Visibility,Params)||
        !VoxelGrounding::ResolveMountingSurface(Surface)||
        FVector::DotProduct(Surface.ImpactNormal,Axis)<.5)return false;
    // A removed voxel may still have its old render/collision mesh until the chunk rebuild finishes.
    FVoxelBuildKey Key;
    return Surface.GetActor()!=this||ResolveHit(Surface,Key);
}

void AVoxelBuildWorld::OnVillageSupportChanged(const AVillageDefenseSection& Section)
{
    if(!bReady)return;
    CachedGridRecipe=NAME_None;
    if(!HasAuthority())
    {
        // The bulk snapshot may have solved these anchors before the section, its owner,
        // or its health arrived. Refresh preview connectivity without running collapse.
        if(!SupportGraph||SupportGraph->Nodes.IsEmpty())return;
        const FBox Bounds=Section.GetComponentsBoundingBox(true).ExpandBy(CellSizeCm*2.);
        TOptional<FCollisionQueryParams> GroundParams;
        bool bChanged=false;
        for(auto& Entry:SupportGraph->Nodes)
        {
            auto& Node=Entry.Value;
            if(!Bounds.IsInsideOrOn(Node.Min))continue;
            if(!GroundParams.IsSet())GroundParams=VoxelGrounding::Query(GetWorld(),this);
            const bool bSupported=HasVoxelFoundation(Entry.Key,GroundParams.GetValue());
            if(Node.bAnchor==bSupported)continue;
            Node.bAnchor=bSupported;
            bChanged=true;
        }
        if(bChanged){++Revision;SupportGraph->SolveConnectivity();}
        return;
    }
    const UStaticMeshComponent* Body=Section.GetMasonry();
    if(!Body||!Body->GetStaticMesh()||(PrefabCellOwners.IsEmpty()&&(!SupportGraph||SupportGraph->Nodes.IsEmpty())))return;
    const FBox Bounds=Body->Bounds.GetBox();
    const FIntVector Min=ToCell(Bounds.Min),Max=ToCell(Bounds.Max);
    TArray<FIntVector> Region;
    TSet<FIntVector> Dependents;
    const bool bRestored=Section.GetHealth()>0.f;
    for(int32 Z=Min.Z;Z<=Max.Z;++Z)for(int32 Y=Min.Y;Y<=Max.Y;++Y)for(int32 X=Min.X;X<=Max.X;++X)
    {
        const FIntVector Cell(X,Y,Z);
        Region.Add(Cell);
        if(!bRestored&&!PrefabCellOwners.IsEmpty())AddNearbyPrefabOwners(Cell,Dependents);
    }
    ReanchorVoxelsAround(Region,true,bRestored);
    if(const auto* Carrier=Cast<AVoxelBuildPrefabActor>(Section.GetAttachParentActor()))
        Dependents.Remove(Carrier->AnchorCell());
    DropUnsupportedPrefabs(Dependents);
}
