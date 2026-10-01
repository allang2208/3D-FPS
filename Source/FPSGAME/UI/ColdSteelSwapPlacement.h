#pragma once
#include "ColdSteelInventoryTypes.h"

namespace ColdSteelInventory
{
// Only displaced instances are repacked. Fixed neighbours and item metadata stay intact.
// The caller owns the transaction; an exhausted search never publishes a partial layout.
// Container scopes the occupancy scan and the repacked rows' storage affiliation when
// Place is the warehouse grid; pass "" (default) for backpack moves and the main warehouse.
// Equipment returns may opt into rotation after all original-orientation passes fail.
inline bool PlaceDisplaced(TArray<FColdSteelItem>& Items, TArray<FColdSteelItem> Displaced,
    const FColdSteelItem& Source, int32 TargetCell, bool& Exhausted,int32 Place=0,int32 PageStart=0,int32 Rows=4,const FString& Container=FString(),bool AutoRotate=false)
{
    struct FCandidate { int32 Cell, Outside, Distance, Height; uint32 Mask; bool bTurned; };
    struct FEntry { FColdSteelItem Item; TArray<FCandidate> Candidates; };
    TArray<FEntry> Entries;
    TArray<uint32> Occupied;Occupied.Init(0,Rows);
    for(const auto& I:Items) if(I.Place==Place&&I.Container==Container&&I.Cell>=PageStart&&I.Cell<PageStart+Rows*18)
        for(int32 Y=0;Y<I.Height;++Y){const int32 Row=(I.Cell-PageStart)/18+Y;
            // 行数由调用方按当前背包装备传入；跨行物品只可能溢出到更高行（那里不会产生
            // 候选位），钳掉越界写防止掩码数组越界崩溃。
            if(Row>=0&&Row<Rows)Occupied[Row]|=((1u<<I.Width)-1)<< (I.Cell%18);}
    for(const auto& I:Displaced)
    {
        FEntry Entry; Entry.Item=I;
        // Equipment slot numbers are not grid coordinates. Returned gear shares
        // the vacated bag anchor; ordinary grid swaps retain their relative offset.
        const bool KeepOffset=Displaced.Num()>1&&(!AutoRotate||I.Place==Place);
        const int32 PreferredX=Source.Cell%18+(KeepOffset?I.Cell%18-TargetCell%18:0);
        const int32 PreferredY=(Source.Cell-PageStart)/18+(KeepOffset?I.Cell/18-TargetCell/18:0);
        const int32 Orientations=AutoRotate&&CanRotate(I)?2:1;
        for(int32 Turn=0;Turn<Orientations;++Turn)
        {
            auto Shape=I;if(Turn)ApplyOrientation(Shape,I.bRotated?0:1);
            for(int32 Y=0;Y+Shape.Height<=Rows;++Y) for(int32 X=0;X+Shape.Width<=18;++X)
            {
                const uint32 Mask=((1u<<Shape.Width)-1)<<X;
                bool Free=true;for(int32 Row=Y;Row<Y+Shape.Height;++Row) if(Occupied[Row]&Mask){Free=false;break;}
                if(!Free)continue;
                const int32 InsideW=FMath::Max(0,FMath::Min(X+Shape.Width,Source.Cell%18+Source.Width)-FMath::Max(X,Source.Cell%18));
                const int32 InsideH=FMath::Max(0,FMath::Min(Y+Shape.Height,(Source.Cell-PageStart)/18+Source.Height)-FMath::Max(Y,(Source.Cell-PageStart)/18));
                Entry.Candidates.Add({PageStart+Y*18+X,Shape.Width*Shape.Height-InsideW*InsideH,FMath::Abs(X-PreferredX)+FMath::Abs(Y-PreferredY),Shape.Height,Mask,Turn!=0});
            }
        }
        if(Entry.Candidates.IsEmpty())return false;
        Entry.Candidates.Sort([](const auto& A,const auto& B){
            if(A.Outside!=B.Outside)return A.Outside<B.Outside;
            if(A.bTurned!=B.bTurned)return !A.bTurned;
            if(A.Distance!=B.Distance)return A.Distance<B.Distance;
            return A.Cell<B.Cell;
        });
        Entries.Add(MoveTemp(Entry));
    }
    Entries.Sort([](const auto& A,const auto& B){
        if(A.Item.Width*A.Item.Height!=B.Item.Width*B.Item.Height)return A.Item.Width*A.Item.Height>B.Item.Width*B.Item.Height;
        if(A.Candidates.Num()!=B.Candidates.Num())return A.Candidates.Num()<B.Candidates.Num();
        if(A.Item.Cell!=B.Item.Cell)return A.Item.Cell<B.Item.Cell;
        return A.Item.InstanceId<B.Item.InstanceId;
    });
    TArray<int32> Choices;Choices.SetNum(Entries.Num());
    // Bound pointer-hover work by candidate visits, including failed collision checks.
    int32 Budget=20000;
    auto Search=[&](auto&& Self,int32 Depth,bool SourceOnly,bool AllowTurns)->bool
    {
        if(Depth==Entries.Num())return true;
        const auto& E=Entries[Depth];
        for(int32 Choice=0;Choice<E.Candidates.Num();++Choice)
        {
            const auto& C=E.Candidates[Choice];
            if((SourceOnly&&C.Outside)||(!AllowTurns&&C.bTurned))continue;
            if(--Budget<0){Exhausted=true;return false;}
            const int32 Row=(C.Cell-PageStart)/18;
            bool Free=true;for(int32 Y=Row;Y<Row+C.Height;++Y)if(Occupied[Y]&C.Mask){Free=false;break;}
            if(!Free)continue;
            for(int32 Y=Row;Y<Row+C.Height;++Y)Occupied[Y]|=C.Mask;
            Choices[Depth]=Choice;
            if(Self(Self,Depth+1,SourceOnly,AllowTurns))return true;
            for(int32 Y=Row;Y<Row+C.Height;++Y)Occupied[Y]&=~C.Mask;
            if(Exhausted)return false;
        }
        return false;
    };
    bool AnyExhausted=false;
    const auto Pass=[&](bool SourceOnly,bool AllowTurns)
    {
        Budget=20000;Exhausted=false;
        const bool Placed=Search(Search,0,SourceOnly,AllowTurns);
        AnyExhausted|=Exhausted;return Placed;
    };
    // Preserve existing orientations wherever a complete layout is available.
    // Each failed pass fully unwinds its masks; Items changes only on success.
    bool Placed=Pass(true,false)||Pass(false,false);
    if(!Placed&&AutoRotate)Placed=Pass(true,true)||Pass(false,true);
    if(!Placed){Exhausted=AnyExhausted;return false;}
    Exhausted=false;
    for(int32 N=0;N<Entries.Num();++N)
    {
        auto I=Entries[N].Item;const auto& C=Entries[N].Candidates[Choices[N]];
        if(C.bTurned)ApplyOrientation(I,I.bRotated?0:1);
        I.Place=Place;I.Container=Container;I.Cell=C.Cell;Items.Add(MoveTemp(I));
    }
    return true;
}
}
