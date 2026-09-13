#include "VoxelSupportGraph.h"

namespace VoxelSupport
{
    constexpr double Size=20,ContactTolerance=.2,MinContactArea=100;
    FIntVector Bucket(const FVector& P){return FIntVector(FMath::FloorToInt(P.X/Size),FMath::FloorToInt(P.Y/Size),FMath::FloorToInt(P.Z/Size));}
}

TArray<int32> FVoxelSupportGraph::Near(const FVector& Min) const
{
    const FIntVector Center=VoxelSupport::Bucket(Min);TArray<int32> Result;
    // Two buckets include a face within the 2 mm contact tolerance even when
    // the continuous origin straddles a bucket boundary.
    for(int32 Z=-2;Z<=2;++Z)for(int32 Y=-2;Y<=2;++Y)for(int32 X=-2;X<=2;++X)
        if(const auto* Entries=Buckets.Find(Center+FIntVector(X,Y,Z)))Result.Append(*Entries);
    return Result;
}

float FVoxelSupportGraph::ContactSpan(const FVector& From,const FVector& To)
{
    using namespace VoxelSupport;
    if(To.Z<From.Z-ContactTolerance)return -1;
    for(int32 Axis=0;Axis<3;++Axis)
    {
        if(FMath::Abs(From[Axis]+Size-To[Axis])>ContactTolerance&&FMath::Abs(To[Axis]+Size-From[Axis])>ContactTolerance)continue;
        const int32 U=(Axis+1)%3,V=(Axis+2)%3;
        const double A=FMath::Min(From[U]+Size,To[U]+Size)-FMath::Max(From[U],To[U]);
        const double B=FMath::Min(From[V]+Size,To[V]+Size)-FMath::Max(From[V],To[V]);
        if(A>0&&B>0&&A*B>=MinContactArea)
            return float(FVector2D(To.X-From.X,To.Y-From.Y).Size());
    }
    return -1;
}

void FVoxelSupportGraph::Add(const FVoxelSupportNode& Node)
{
    const int32 Index=Nodes.Add(Node);Edges.AddDefaulted();Indices.Add(Node.Key,Index);
    for(int32 Other:Near(Node.Min))
    {
        const float Forward=ContactSpan(Nodes[Other].Min,Node.Min),Back=ContactSpan(Node.Min,Nodes[Other].Min);
        if(Forward>=0)Edges[Other].Add({Index,Forward});
        if(Back>=0)Edges[Index].Add({Other,Back});
    }
    Buckets.FindOrAdd(VoxelSupport::Bucket(Node.Min)).Add(Index);
}

void FVoxelSupportGraph::Solve()
{
    Cost.Init(TNumericLimits<float>::Max(),Nodes.Num());TArray<int32> Queue;
    for(int32 I=0;I<Nodes.Num();++I)if(Nodes[I].bAnchor){Cost[I]=0;Queue.Add(I);}
    for(int32 Read=0;Read<Queue.Num();++Read)
    {
        const int32 Source=Queue[Read];if(!Nodes[Source].bBearing)continue;
        for(const auto& Edge:Edges[Source])
        {
            const float Candidate=Cost[Source]+Edge.SpanCm;
            if(Candidate<=MaxSpanCm+.01f&&Candidate+.001f<Cost[Edge.Target])
            {Cost[Edge.Target]=Candidate;Queue.Add(Edge.Target);}
        }
    }
}

bool FVoxelSupportGraph::IsSupported(int32 Index) const
{
    return Cost.IsValidIndex(Index)&&Cost[Index]<=MaxSpanCm+.01f;
}

bool FVoxelSupportGraph::Overlaps(const FVector& Min) const
{
    const FBox Box(Min+FVector(.05),Min+FVector(19.95));
    for(int32 Index:Near(Min))
        if(Box.Intersect(FBox(Nodes[Index].Min+FVector(.05),Nodes[Index].Min+FVector(19.95))))return true;
    return false;
}
