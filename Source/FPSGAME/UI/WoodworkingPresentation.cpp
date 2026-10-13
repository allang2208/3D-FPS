#include "WoodworkingPresentation.h"

void WoodworkingPresentation::ClosePolyline(TArray<FVector2D>& Points)
{
    if(Points.Num()<2||Points[0]==Points.Last())return;
    // TArray::Add rejects references into its own allocation, even with spare capacity.
    const FVector2D FirstPoint=Points[0];
    Points.Add(FirstPoint);
}

void WoodworkingPresentation::TargetContours(const TArray<uint8>& Mask,int32 Width,int32 Height,TArray<TArray<FVector2D>>& Out)
{
    Out.Reset();if(Mask.Num()!=Width*Height)return;
    // Grid edges, not the source polygon: the visible guide matches the raster used by scoring.
    TMap<FIntPoint,TArray<FIntPoint,TInlineAllocator<2>>> Edges;
    auto Add=[&](FIntPoint A,FIntPoint B){Edges.FindOrAdd(A).Add(B);};
    for(int32 Y=0;Y<Height;++Y)for(int32 X=0;X<Width;++X)if(Mask[Y*Width+X])
    {
        if(Y==0||!Mask[(Y-1)*Width+X])Add({X,Y},{X+1,Y});
        if(X==Width-1||!Mask[Y*Width+X+1])Add({X+1,Y},{X+1,Y+1});
        if(Y==Height-1||!Mask[(Y+1)*Width+X])Add({X+1,Y+1},{X,Y+1});
        if(X==0||!Mask[Y*Width+X-1])Add({X,Y+1},{X,Y});
    }
    while(!Edges.IsEmpty())
    {
        const FIntPoint First=Edges.CreateConstIterator().Key();FIntPoint At=First;
        TArray<FVector2D> Path;Path.Add(FVector2D(At));
        do
        {
            auto* Nexts=Edges.Find(At);if(!Nexts||Nexts->IsEmpty())break;
            const FIntPoint Next=Nexts->Pop(EAllowShrinking::No);if(Nexts->IsEmpty())Edges.Remove(At);
            const FVector2D Point(Next);
            if(Path.Num()>1&&FMath::Abs(FVector2D::CrossProduct(Path.Last()-Path[Path.Num()-2],Point-Path.Last()))<.001)
                Path.Last()=Point;
            else Path.Add(Point);
            At=Next;
        }while(At!=First);
        if(Path.Num()>1)Out.Add(MoveTemp(Path));
    }
}
