#include "FoodSpoilage.h"
#include "FoodSpoilageClock.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace ColdSteelFood
{
namespace {TMap<FString,double> CatalogLifetimes;}
void RegisterCatalog(const TMap<FString,FString>& Definitions)
{
    CatalogLifetimes.Reset();
    for(const auto& Pair:Definitions)
    {
        TSharedPtr<FJsonObject> Data;double Days=0.;
        if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Pair.Value),Data)&&Data
            &&Data->TryGetNumberField(TEXT("spoilDays"),Days)&&FMath::IsFinite(Days)&&Days>0.)
            CatalogLifetimes.Add(Pair.Key,Days);
    }
}
FFoodClockSample Clock(const UObject* Context)
{
    UWorld* W=Context?Context->GetWorld():nullptr;
    if(!W)return {};
    if(W->GetNetMode()==NM_Client)
    {
        const auto* GI=W->GetGameInstance();
        const auto* M=GI?GI->GetSubsystem<UColdSteelStatusModel>():nullptr;
        return M?M->FoodClockSnapshot():FFoodClockSample{};
    }
    auto* C=W->GetSubsystem<UFoodSpoilageClock>();
    return C?C->Sample():FFoodClockSample{};
}

double LifetimeDays(const FColdSteelItem& I)
{
    // Definition-owned, bounded startup cache. Old or uploaded instance JSON
    // cannot disable spoilage or extend an authored lifetime.
    return CatalogLifetimes.FindRef(I.Definition);
}

double AgeDays(const FColdSteelItem& I,const FFoodClockSample& Now)
{
    if(I.FoodVersion==0)return 0.;
    if(!FMath::IsFinite(I.FoodAgeDays)||!FMath::IsFinite(I.FoodSampleDay))return LifetimeDays(I);
    const double Elapsed=I.FoodClockId.IsValid()&&I.FoodClockId==Now.Id?FMath::Max(0.,Now.Day-I.FoodSampleDay):0.;
    return FMath::Max(0.,I.FoodAgeDays)+Elapsed;
}
bool IsExpired(const FColdSteelItem& I,const FFoodClockSample& Now)
{const double Life=LifetimeDays(I);return Life>0.&&AgeDays(I,Now)>=Life;}

void Stamp(FColdSteelItem& I,const FFoodClockSample& Now,double Age)
{
    if(LifetimeDays(I)<=0.)return;
    I.FoodVersion=1;I.FoodClockId=Now.Id;I.FoodSampleDay=FMath::Max(0.,Now.Day);
    I.FoodAgeDays=FMath::IsFinite(Age)?FMath::Max(0.,Age):LifetimeDays(I);
}
bool Rebase(FColdSteelItem& I,const FFoodClockSample& Now)
{
    if(LifetimeDays(I)<=0.||!Now.Id.IsValid())return false;
    if(I.FoodVersion>0&&I.FoodClockId==Now.Id)return false;
    Stamp(I,Now,AgeDays(I,Now));return true;
}
bool RebaseProfile(FColdSteelProfile& P,const FFoodClockSample& Now)
{
    if(!Now.Id.IsValid())return false;
    const FFoodClockSample Previous{P.FoodClockId,P.FoodClockDay};bool Changed=false;
    for(auto& I:P.Items)
    {
        if(I.Container.StartsWith(TEXT("NetView."))||LifetimeDays(I)<=0.)continue;
        if(I.FoodVersion>0&&(I.FoodClockId!=Now.Id
            ||(Previous.Id==Now.Id&&Previous.Day>Now.Day)))
        {const double Age=AgeDays(I,Previous);Stamp(I,Now,Age);Changed=true;}
        else Changed|=Rebase(I,Now);
    }
    Changed|=P.FoodVersion!=1||P.FoodClockId!=Now.Id||P.FoodClockDay!=Now.Day;
    P.FoodVersion=1;P.FoodClockId=Now.Id;P.FoodClockDay=Now.Day;return Changed;
}
bool Compatible(const FColdSteelItem& A,const FColdSteelItem& B)
{
    if(LifetimeDays(A)<=0.&&LifetimeDays(B)<=0.)return true;
    // Compare birth position on the same natural clock, not rounded freshness.
    // Splitting retains it exactly. Newly acquired food cannot refresh an older batch.
    return A.FoodVersion>0&&B.FoodVersion>0&&A.FoodClockId==B.FoodClockId
        &&A.FoodSampleDay-A.FoodAgeDays==B.FoodSampleDay-B.FoodAgeDays;
}

namespace
{
bool Yield(const FColdSteelItem& I,int64& Count,FString& Reason)
{
    const int64 Area=int64(I.Width)*I.Height;
    if(Area<1||I.Count<1||I.Count>MAX_int64/Area)
    {Reason=TEXT("食物数量无效，原物品保留");return false;}
    Count=Area*I.Count;
    if(Count>100000)
    {Reason=TEXT("腐败产物过多，原过期食物保留且不可使用");return false;}
    return true;
}
FColdSteelItem Product(const FColdSteelItem& Source,const UColdSteelStatusModel* M,int64 Count)
{
    auto I=M->CreateItem(TEXT("spoiled_food"),Count);
    I.Place=Source.Place;I.Cell=Source.Cell;I.BackpackCell=Source.BackpackCell;I.Container=Source.Container;
    I.Map=Source.Map;I.Position=Source.Position;I.WorldRotation=Source.WorldRotation;I.HarvestWorldId=Source.HarvestWorldId;
    I.Width=I.Height=1;I.StackMax=10;I.bRotated=false;return I;
}
bool SameStorage(const FColdSteelItem& A,const FColdSteelItem& B)
{return A.Place==B.Place&&A.Container==B.Container&&A.Map==B.Map&&A.HarvestWorldId==B.HarvestWorldId;}
}

bool SettleLoose(TArray<FColdSteelItem>& Items,const UColdSteelStatusModel* Model,const FFoodClockSample& Now,FString& Reason)
{
    Reason.Reset();if(!Model||!Now.Id.IsValid())return false;
    auto Next=Items;bool Changed=false;
    for(int32 N=Next.Num()-1;N>=0;--N)
    {
        auto& I=Next[N];if(I.Container.StartsWith(TEXT("NetView.")))continue;
        Changed|=Rebase(I,Now);if(!IsExpired(I,Now))continue;
        int64 Remaining=0;if(!Yield(I,Remaining,Reason))return false;
        const auto Source=I;Next.RemoveAt(N);
        while(Remaining>0)
        {
            const int64 Count=FMath::Min<int64>(10,Remaining);auto Out=Product(Source,Model,Count);
            if(Out.Data.IsEmpty()){Reason=TEXT("腐败食物定义缺失，原食物保留");return false;}
            Next.Add(MoveTemp(Out));Remaining-=Count;
        }
        Changed=true;
    }
    if(Changed)Items=MoveTemp(Next);return Changed;
}

bool SettleGrid(TArray<FColdSteelItem>& Items,const UColdSteelStatusModel* Model,const FFoodClockSample& Now,FString& Reason)
{
    Reason.Reset();if(!Model||!Now.Id.IsValid())return false;
    auto Next=Items;TArray<FColdSteelItem> Expired;bool Changed=false;
    for(int32 N=Next.Num()-1;N>=0;--N)
    {
        auto& I=Next[N];if(I.Container.StartsWith(TEXT("NetView.")))continue;
        Changed|=Rebase(I,Now);
        if(IsExpired(I,Now)){Expired.Add(I);Next.RemoveAt(N);Changed=true;}
    }
    // Every current food is a single item. Even a completely full grid has at
    // least its old footprint available, enough for area/10 one-cell stacks.
    for(const auto& Old:Expired)
    {
        int64 Remaining=0;if(!Yield(Old,Remaining,Reason))return false;
        auto Out=Product(Old,Model,1);
        if(Out.Data.IsEmpty()){Reason=TEXT("腐败食物定义缺失，原食物保留");return false;}
        if(Old.Place==2)
        {
            while(Remaining>0){auto Part=Product(Old,Model,FMath::Min<int64>(10,Remaining));Remaining-=Part.Count;Next.Add(MoveTemp(Part));}
            continue;
        }
        for(auto& Existing:Next)
        {
            if(Existing.Definition!=TEXT("spoiled_food")||!SameStorage(Existing,Old))continue;
            const int64 Amount=FMath::Min(Remaining,FMath::Max<int64>(0,10-Existing.Count));
            Existing.Count+=Amount;Remaining-=Amount;if(!Remaining)break;
        }
        const int32 Columns=Old.Place==ColdSteelInventory::ColdSteelCompartment::Place?ColdSteelInventory::CompartmentGrid(Items).X:18;
        if(Columns<1){Reason=TEXT("食物存储布局不可用，原过期食物保留");return false;}
        for(int32 Y=0;Y<Old.Height&&Remaining>0;++Y)for(int32 X=0;X<Old.Width&&Remaining>0;++X)
        {
            const int32 Cell=Old.Cell+Y*Columns+X;
            const bool Occupied=Next.ContainsByPredicate([&](const FColdSteelItem& V)
            {return SameStorage(V,Old)&&Cell%Columns>=V.Cell%Columns&&Cell%Columns<V.Cell%Columns+V.Width
                &&Cell/Columns>=V.Cell/Columns&&Cell/Columns<V.Cell/Columns+V.Height;});
            if(Occupied)continue;
            auto Part=Product(Old,Model,FMath::Min<int64>(10,Remaining));Part.Cell=Cell;
            Remaining-=Part.Count;Next.Add(MoveTemp(Part));
        }
        if(Remaining>0)
        {Reason=TEXT("空间不足以完整保存腐败产物，原过期食物保留且不可使用");return false;}
    }
    if(Changed)Items=MoveTemp(Next);return Changed;
}
}
