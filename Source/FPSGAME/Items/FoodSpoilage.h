#pragma once
#include "CoreMinimal.h"

struct FColdSteelItem;
struct FColdSteelProfile;
class UColdSteelStatusModel;

struct FFoodClockSample
{
    FGuid Id;
    double Day=0.;
};

/** Natural game days only. Moving an item never creates a fresh lifetime. */
namespace ColdSteelFood
{
    void RegisterCatalog(const TMap<FString,FString>& Definitions);
    FFoodClockSample Clock(const UObject* Context);
    double LifetimeDays(const FColdSteelItem& Item);
    double AgeDays(const FColdSteelItem& Item,const FFoodClockSample& Now);
    bool IsExpired(const FColdSteelItem& Item,const FFoodClockSample& Now);
    void Stamp(FColdSteelItem& Item,const FFoodClockSample& Now,double Age=0.);
    bool Rebase(FColdSteelItem& Item,const FFoodClockSample& Now);
    bool RebaseProfile(FColdSteelProfile& Profile,const FFoodClockSample& Now);
    bool Compatible(const FColdSteelItem& A,const FColdSteelItem& B);
    // false + empty Reason means unchanged. Failure leaves the complete array intact.
    bool SettleLoose(TArray<FColdSteelItem>& Items,const UColdSteelStatusModel* Model,const FFoodClockSample& Now,FString& Reason);
    bool SettleGrid(TArray<FColdSteelItem>& Items,const UColdSteelStatusModel* Model,const FFoodClockSample& Now,FString& Reason);
}
