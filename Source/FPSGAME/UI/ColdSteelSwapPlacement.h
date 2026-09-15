#pragma once
#include "ColdSteelInventoryTypes.h"

namespace ColdSteelInventory
{
// Only displaced instances are repacked. Fixed neighbours and item metadata stay intact.
// The caller owns the transaction; an exhausted search never publishes a partial layout.
inline bool PlaceDisplaced(TArray<FColdSteelItem>& Items, TArray<FColdSteelItem> Displaced,
    const FColdSteelItem& Source, int32 TargetCell, bool& Exhausted,int32 Place=0,int32 PageStart=0,int32 Rows=4)
{
    struct FCandidate { int32 Cell, Outside, Distance; uint32 Mask; };
    struct FEntry { FColdSteelItem Item; TArray<FCandidate> Candidates; };
    TArray<FEntry> Entries;
    TArray<uint32> Occupied;Occupied.Init(0,Rows);
    for(const auto& I:Items) if(I.Place==Place&&I.Cell>=PageStart&&I.Cell<PageStart+Rows*18)
        for(int32 Y=0;Y<I.Height;++Y) Occupied[(I.Cell-PageStart)/18+Y]|=((1u<<I.Width)-1)<< (I.Cell%18);
    for(const auto& I:Displaced)
    {
        FEntry Entry; Entry.Item=I;
        const int32 PreferredX=Source.Cell%18+(Displaced.Num()==1?0:I.Cell%18-TargetCell%18);
        const int32 PreferredY=(Source.Cell-PageStart)/18+(Displaced.Num()==1?0:I.Cell/18-TargetCell/18);
        for(int32 Y=0;Y+I.Height<=Rows;++Y) for(int32 X=0;X+I.Width<=18;++X)
        {
            const uint32 Mask=((1u<<I.Width)-1)<<X;
            bool Free=true;for(int32 Row=Y;Row<Y+I.Height;++Row) if(Occupied[Row]&Mask){Free=false;break;}
            if(!Free)continue;
            const int32 InsideW=FMath::Max(0,FMath::Min(X+I.Width,Source.Cell%18+Source.Width)-FMath::Max(X,Source.Cell%18));
            const int32 InsideH=FMath::Max(0,FMath::Min(Y+I.Height,(Source.Cell-PageStart)/18+Source.Height)-FMath::Max(Y,(Source.Cell-PageStart)/18));
            Entry.Candidates.Add({PageStart+Y*18+X,I.Width*I.Height-InsideW*InsideH,FMath::Abs(X-PreferredX)+FMath::Abs(Y-PreferredY),Mask});
        }
        if(Entry.Candidates.IsEmpty())return false;
        Entry.Candidates.Sort([](const auto& A,const auto& B){
            if(A.Outside!=B.Outside)return A.Outside<B.Outside;
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
    TArray<int32> Cells;Cells.SetNum(Entries.Num());
    // Bound pointer-hover work by candidate visits, including failed collision checks.
    int32 Budget=20000;
    auto Search=[&](auto&& Self,int32 Depth,bool SourceOnly)->bool
    {
        if(Depth==Entries.Num())return true;
        const auto& E=Entries[Depth];
        for(const auto& C:E.Candidates)
        {
            if(SourceOnly&&C.Outside)continue;
            if(--Budget<0){Exhausted=true;return false;}
            const int32 Row=(C.Cell-PageStart)/18;
            bool Free=true;for(int32 Y=Row;Y<Row+E.Item.Height;++Y)if(Occupied[Y]&C.Mask){Free=false;break;}
            if(!Free)continue;
            for(int32 Y=Row;Y<Row+E.Item.Height;++Y)Occupied[Y]|=C.Mask;
            Cells[Depth]=C.Cell;
            if(Self(Self,Depth+1,SourceOnly))return true;
            for(int32 Y=Row;Y<Row+E.Item.Height;++Y)Occupied[Y]&=~C.Mask;
            if(Exhausted)return false;
        }
        return false;
    };
    if(!Search(Search,0,true))
    {
        // Reserve an independent bounded pass for nearby empty cells.
        Budget=20000;Exhausted=false;
        if(!Search(Search,0,false))return false;
    }
    for(int32 N=0;N<Entries.Num();++N){auto I=Entries[N].Item;I.Place=Place;I.Cell=Cells[N];Items.Add(MoveTemp(I));}
    return true;
}
}
