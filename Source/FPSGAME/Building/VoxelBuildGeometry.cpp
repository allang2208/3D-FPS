#include "VoxelBuildGeometry.h"
#include "VoxelSurfaceMesher.h"
#include "VoxelSupportGraph.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "DynamicMeshEditor.h"

namespace
{
    int32 Floor16(int32 N){return N>=0?N/16:-int32((-(int64)N+15)/16);}
    FIntVector ChunkOf(FIntVector P){return FIntVector(Floor16(P.X),Floor16(P.Y),Floor16(P.Z));}
    void Boxes(TSet<FIntVector> Remaining,FVector Offset,FKAggregateGeom& Out)
    {
        TArray<FIntVector> Ordered=Remaining.Array();
        Ordered.Sort([](FIntVector A,FIntVector B){return A.Z!=B.Z?A.Z<B.Z:(A.Y!=B.Y?A.Y<B.Y:A.X<B.X);});
        for(FIntVector P:Ordered)
        {
            if(!Remaining.Contains(P))continue;
            int32 W=1,H=1,D=1;
            while(Remaining.Contains(P+FIntVector(W,0,0)))++W;
            auto Row=[&](int32 Y,int32 Z){for(int32 X=0;X<W;++X)if(!Remaining.Contains(P+FIntVector(X,Y,Z)))return false;return true;};
            while(Row(H,0))++H;
            auto Layer=[&](int32 Z){for(int32 Y=0;Y<H;++Y)if(!Row(Y,Z))return false;return true;};
            while(Layer(D))++D;
            FKBoxElem Box;Box.X=W*20;Box.Y=H*20;Box.Z=D*20;
            Box.Center=Offset+FVector(P)*20+FVector(Box.X,Box.Y,Box.Z)*.5;Out.BoxElems.Add(Box);
            for(int32 Z=0;Z<D;++Z)for(int32 Y=0;Y<H;++Y)for(int32 X=0;X<W;++X)Remaining.Remove(P+FIntVector(X,Y,Z));
        }
    }
    struct FVolume { FVector Offset;TMap<FIntVector,int32> Cells;TSet<FIntVector> Chunks; };
    TMap<FGuid,FVolume> Volumes(const TArray<FVoxelDebrisCell>& Cells,const TMap<FName,int32>& Slots)
    {
        TMap<FGuid,FVolume> Result;
        for(const auto& Cell:Cells)
        {
            auto& V=Result.FindOrAdd(Cell.Key.Volume);V.Offset=Cell.Min-FVector(Cell.Key.Cell)*20;
            V.Cells.Add(Cell.Key.Cell,Slots.FindRef(Cell.Material));V.Chunks.Add(ChunkOf(Cell.Key.Cell));
        }
        return Result;
    }
}

TSharedPtr<FVoxelGeometry> VoxelGeometry::Chunk(FIntVector Origin,TMap<FIntVector,int32> Slots,double Radius)
{
    auto Result=MakeShared<FVoxelGeometry>();
    VoxelSurface::Build(Result->Mesh,Origin,16,Radius,[&](FIntVector P){const auto* S=Slots.Find(P);return S?*S:INDEX_NONE;});
    TSet<FIntVector> Occupied;
    for(const auto& E:Slots){const auto P=E.Key-Origin;if(P.X>=0&&P.Y>=0&&P.Z>=0&&P.X<16&&P.Y<16&&P.Z<16)Occupied.Add(P);}
    Boxes(MoveTemp(Occupied),FVector::ZeroVector,Result->Collision);return Result;
}

TSharedPtr<FVoxelGeometry> VoxelGeometry::Batch(TArray<FVoxelChunkSnapshot> Chunks,double Radius)
{
    using namespace UE::Geometry;
    auto Result=MakeShared<FVoxelGeometry>();Result->Mesh.EnableAttributes();Result->Mesh.Attributes()->EnableMaterialID();
    for(auto& Input:Chunks)
    {
        auto Part=Chunk(Input.Origin,MoveTemp(Input.Slots),Radius);
        FDynamicMeshEditor Editor(&Result->Mesh);FMeshIndexMappings Maps;const FVector3d Offset(Input.Offset);
        Editor.AppendMesh(&Part->Mesh,Maps,[Offset](int32,const FVector3d& P){return P+Offset;});
        for(auto Box:Part->Collision.BoxElems){Box.Center+=Input.Offset;Result->Collision.BoxElems.Add(Box);}
    }
    return Result;
}

TSharedPtr<FVoxelGeometry> VoxelGeometry::Fragment(const TArray<FVoxelDebrisCell>& Cells,
    const TMap<FName,int32>& Slots,const TMap<FName,float>& Densities,double Radius)
{
    using namespace UE::Geometry;
    auto Result=MakeShared<FVoxelGeometry>();Result->Mesh.EnableAttributes();Result->Mesh.Attributes()->EnableMaterialID();
    for(const auto& Cell:Cells)
    {
        const float Mass=FMath::Max(.001f,Densities.FindRef(Cell.Material)*.008f);
        Result->MassKg+=Mass;Result->MassCenter+=(Cell.Min+FVector(10))*Mass;
    }
    if(Result->MassKg>0)Result->MassCenter/=Result->MassKg;
    for(const auto& Pair:Volumes(Cells,Slots))
    {
        const auto& V=Pair.Value;TSet<FIntVector> Occupied;
        for(const auto& E:V.Cells)Occupied.Add(E.Key);
        Boxes(MoveTemp(Occupied),V.Offset,Result->Collision);
        for(FIntVector C:V.Chunks)
        {
            FDynamicMesh3 Part;const FIntVector Origin=C*16;
            VoxelSurface::Build(Part,Origin,16,Radius,[&](FIntVector P){const auto* S=V.Cells.Find(P);return S?*S:INDEX_NONE;});
            const FVector3d Translation(V.Offset+FVector(Origin)*20);
            FDynamicMeshEditor Editor(&Result->Mesh);FMeshIndexMappings Maps;
            Editor.AppendMesh(&Part,Maps,[Translation](int32,const FVector3d& P){return P+Translation;});
        }
    }
    return Result;
}

TArray<FVoxelFragmentSave> VoxelGeometry::Split(const FVoxelFragmentSave& Source,const TSet<FVoxelBrokenBond>& Broken,int32 MaxShapes)
{
    FVoxelSupportGraph Graph;Graph.Broken=Broken;Graph.Broken.Append(Source.BrokenBonds);TMap<FVoxelBuildKey,int32> Indices;
    for(int32 I=0;I<Source.Cells.Num();++I)
    {const auto& C=Source.Cells[I];Graph.Add({C.Key,C.Min});Indices.Add(C.Key,I);}
    TArray<FVoxelFragmentSave> Result;TSet<FVoxelBuildKey> Seen;
    for(const auto& Entry:Graph.Nodes)
    {
        if(Seen.Contains(Entry.Key))continue;
        TArray<FVoxelBuildKey> Queue{Entry.Key};Seen.Add(Entry.Key);
        for(int32 Read=0;Read<Queue.Num();++Read)
        {
            const auto Key=Queue[Read];if(const auto* Next=Graph.Edges.Find(Key))for(const auto& N:*Next)
                if(!Seen.Contains(N)){Seen.Add(N);Queue.Add(N);}
        }
        FVoxelFragmentSave Part=Source;Part.Id=FGuid::NewGuid();Part.Cells.Reset();
        for(const auto& K:Queue)Part.Cells.Add(Source.Cells[Indices.FindChecked(K)]);
        // Merge regular solids first; only geometrically complex islands need
        // spatial subdivision to keep compound rigid-body shape counts bounded.
        TArray<FVoxelFragmentSave> Work;Work.Add(MoveTemp(Part));
        while(!Work.IsEmpty())
        {
            auto Piece=Work.Pop();FKAggregateGeom Collision;TMap<FName,int32> Empty;
            for(const auto& V:Volumes(Piece.Cells,Empty))
            {TSet<FIntVector> Occupied;for(const auto& C:V.Value.Cells)Occupied.Add(C.Key);Boxes(MoveTemp(Occupied),V.Value.Offset,Collision);}
            if(Collision.BoxElems.Num()<=FMath::Max(1,MaxShapes)){Result.Add(MoveTemp(Piece));continue;}
            FBox Bounds(ForceInit);for(const auto& C:Piece.Cells)Bounds+=C.Min;
            const FVector Extent=Bounds.GetSize();const int32 Axis=Extent.X>=Extent.Y&&Extent.X>=Extent.Z?0:(Extent.Y>=Extent.Z?1:2);
            Piece.Cells.Sort([Axis](const auto& A,const auto& B){return A.Min[Axis]<B.Min[Axis];});
            FVoxelFragmentSave Half=Piece;Half.Id=FGuid::NewGuid();const int32 Middle=Piece.Cells.Num()/2;
            Half.Cells.RemoveAt(0,Middle,EAllowShrinking::No);Piece.Cells.SetNum(Middle,EAllowShrinking::No);
            Work.Add(MoveTemp(Piece));Work.Add(MoveTemp(Half));
        }
    }
    // Detached material receives new identities: rebuilding the same static
    // grid coordinate must never repair or damage an older piece of debris.
    for(auto& Part:Result)
    {
        TMap<FGuid,FGuid> VolumesMap;TMap<FVoxelBuildKey,FVoxelBuildKey> Keys;
        for(auto& Cell:Part.Cells)
        {
            if(!VolumesMap.Contains(Cell.Key.Volume))VolumesMap.Add(Cell.Key.Volume,FGuid::NewGuid());
            const auto Previous=Cell.Key;Cell.Key.Volume=VolumesMap.FindChecked(Previous.Volume);Keys.Add(Previous,Cell.Key);
        }
        Part.BrokenBonds.Reset();
        for(const auto& Bond:Graph.Broken)if(Keys.Contains(Bond.A)&&Keys.Contains(Bond.B))
            Part.BrokenBonds.Add({Keys.FindChecked(Bond.A),Keys.FindChecked(Bond.B)});
    }
    return Result;
}
