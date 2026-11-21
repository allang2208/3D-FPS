#include "TemperateVillageCheckCommandlet.h"
#include "../Building/VillageBuildDefense.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelSupportGraph.h"
#include "VillageDefenseSection.h"
#include "Engine/DamageEvents.h"

void UTemperateVillageCheckCommandlet::ExerciseDefenseSupport(AVoxelBuildWorld& Build,FVector Floor,
    TFunctionRef<bool(bool,const FString&)> Check)
{
    using namespace VillageBuildDefense;
    // Isolate a seam cell shared by two discretized shapes from the mesh clearance test.
    FVoxelBuildPrefabInstance Left,Right;
    Left.Id=StoneWall;Left.Cell=Build.ToCell(Floor+FVector(5100,0,0));Left.Footprint=FIntVector(2,1,1);
    Right=Left;Right.Cell.X++;
    TArray<FIntVector> LeftCells,RightCells;
    for(const bool bLeftFirst:{true,false})
    {
        Build.AddPrefabOccupancy(Left,LeftCells);Build.AddPrefabOccupancy(Right,RightCells);
        Build.RemovePrefabOccupancy(bLeftFirst?Left.Cell:Right.Cell,bLeftFirst?LeftCells:RightCells);
        const bool bRetained=Build.IsPrefabCell({},Right.Cell)
            &&Build.PrefabCellOwners.FindPair(Right.Cell,bLeftFirst?Right.Cell:Left.Cell);
        Build.RemovePrefabOccupancy(bLeftFirst?Right.Cell:Left.Cell,bLeftFirst?RightCells:LeftCells);
        Check(bRetained&&!Build.IsPrefabCell({},Right.Cell),bLeftFirst?
            TEXT("Shared seam cell retains the right owner when the left piece is removed first"):
            TEXT("Shared seam cell retains the left owner when the right piece is removed first"));
    }
    const FIntVector BreachBase=Build.ToCell(Floor+FVector(-2200.,1200.,0.));
    if(Check(Build.PlacePrefab(StoneWall,BreachBase),TEXT("Build a repairable wall as a voxel support")))
    {
        auto* Carrier=Build.PrefabActorAt(BreachBase);
        auto* Wall=CastChecked<AVillageDefenseSection>(Carrier->Logic());
        const FIntVector Voxel=BreachBase+FIntVector(7,3,5);
        const bool Placed=Build.EditCells({Voxel},TEXT("wood"));
        const auto Anchored=[&](){
            const auto* Node=Build.SupportGraph->Nodes.Find({FGuid(),Voxel});
            return Node&&Node->bAnchor;
        };
        Check(Placed&&Anchored(),TEXT("A side-mounted voxel is anchored to the intact wall"));
        const auto* Mount=Build.Palette->Components.FindByPredicate([](const FVoxelBuildPrefab& Def){
            return Def.Mount==EVoxelPrefabMount::Wall;
        });
        TOptional<FIntVector> Hanging;
        if(Mount)
            for(int32 Gap=0;Gap<=1&&!Hanging.IsSet();++Gap)
            {
                const FIntVector Cell=BreachBase+FIntVector(2,3+Gap,5);
                if(Build.PlacePrefab(Mount->Id,Cell,1))Hanging=Cell;
            }
        Check(Hanging.IsSet(),TEXT("Wall fixture fastens to the intact stone section"));
        Wall->TakeDamage(Wall->GetMaximumHealth(),FDamageEvent(),nullptr,nullptr);
        Check(Build.IsPrefabCell({},BreachBase)&&Build.PrefabActorAt(BreachBase)==Carrier&&
            !Build.PrefabSupportAt(Build.CellMin(Voxel))&&!Anchored(),
            TEXT("Breach retains its repair plot while immediately releasing the voxel anchor"));
        Check(Hanging.IsSet()&&!Build.HasPrefabAt(Hanging.GetValue()),
            TEXT("Destroying the backing releases the wall-mounted fixture"));
        Build.RemovePrefab(Carrier);
        if(Placed)Build.EditCells({Voxel},NAME_None);
    }
    for(const FName Id:{WoodGate,StoneGate})
    {
        const FIntVector Base=Build.ToCell(Floor+FVector(-900.,1100.,0.));
        if(!Check(Build.PlacePrefab(Id,Base),TEXT("Build a gate for its permanent support surfaces")))continue;
        auto* Carrier=Build.PrefabActorAt(Base);
        auto* Gate=CastChecked<AVillageDefenseSection>(Carrier->Logic());
        const FTransform Frame=Gate->GetActorTransform();
        const FIntVector Opening=Build.ToCell(Frame.TransformPosition(FVector(0,0,100)));
        const FIntVector Pier=Build.ToCell(Frame.TransformPosition(FVector(Id==WoodGate?362.:382.,0.,100.)));
        Check(Build.IsPrefabCell({},Opening)&&!Build.CanBearLoadAt(Base,Opening)&&Build.CanBearLoadAt(Base,Pier),
            Id.ToString()+TEXT(" reserves the closing path but carries weight only on the fixed pier"));
        Gate->TakeDamage(Gate->GetMaximumHealth(),FDamageEvent(),nullptr,nullptr);
        Check(!Build.CanBearLoadAt(Base,Opening)&&Build.CanBearLoadAt(Base,Pier),
            Id.ToString()+TEXT(" keeps its masonry support after the moving gate is broken"));
        Build.RemovePrefab(Carrier);
    }
    // Four 20 cm free voxels lift the footing beyond the ground probes. The slight
    // horizontal offset leaves a real contact face while exercising a non-lattice origin.
    const TArray<FIntVector> Column={{0,0,0},{0,0,1},{0,0,2},{0,0,3}};
    for(const FName Id:{StoneWall,WoodGate})
    {
        const FVector Foot=Floor+FVector(1500.,Id==StoneWall?1400.:2200.,0.);
        const FIntVector Base=Build.ToCell(Foot)+FIntVector(0,0,4);
        if(!Check(Build.PlaceFree(Foot+FVector(5.,4.,0.),Column,TEXT("stone")),
            TEXT("Create offset free-voxel footing for ")+Id.ToString()))return;
        if(!Check(Build.PlacePrefab(Id,Base),TEXT("Free-volume voxel face supports ")+Id.ToString()+TEXT(" ")+Build.ResultMessage()))return;
        AVoxelBuildPrefabActor* Bottom=Build.PrefabActorAt(Base);
        if(!Check(Bottom!=nullptr,TEXT("Raised village carrier is installed")))return;
        if(Id==StoneWall)
        {
            const FIntVector Upper=Base+FIntVector(0,0,11);
            if(!Check(Build.PlacePrefab(StoneWall,Upper),TEXT("Stack a second wall on the raised wall")))return;
            const FIntVector Top=Upper+FIntVector(0,0,11);
            if(!Check(Build.PlacePrefab(StoneWall,Top),TEXT("Stack a third wall on the same footing")))return;
            Check(Build.RemovePrefab(Bottom)&&!Build.HasPrefabAt(Upper)&&!Build.HasPrefabAt(Top)
                &&!Build.IsPrefabCell({},Upper)&&!Build.IsPrefabCell({},Top),
                TEXT("Removing the only supporting wall drops both connected upper walls and releases their occupancy"));
        }
        else
        {
            Check(Build.RemovePrefab(Bottom)&&!Build.IsPrefabCell({},Base),TEXT("Dismantling the timber gate releases its cells"));
        }
    }
}
