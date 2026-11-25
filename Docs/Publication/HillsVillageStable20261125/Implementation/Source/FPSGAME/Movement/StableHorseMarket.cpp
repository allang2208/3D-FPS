#include "StableHorseMarket.h"
#include "GameFramework/Character.h"

bool StableHorseMarket::IsSeller(const AActor* Actor)
{
    static const FName StablemasterTag(TEXT("VillageStable.Stablemaster"));
    static const FName ClassTag(TEXT("VillageStablemaster"));
    return IsValid(Actor) && Actor->IsA<ACharacter>() &&
        (Actor->ActorHasTag(StablemasterTag) || Actor->ActorHasTag(ClassTag));
}
TArray<FStableHorseOffer> StableHorseMarket::Stock(FGuid ProfileId,int32 Day)
{
    TArray<FStableHorseOffer> Offers;
    if(!ProfileId.IsValid() || Day<0)return Offers;
    Offers.Reserve(DailyCount);
    const FString Prefix=FString::Printf(TEXT("StableMarket/R26/%s/%d/"),*ProfileId.ToString(EGuidFormats::Digits),Day);
    TBitArray<> UsedNames(false,FStableHorseTraits::NameCount);
    for(int32 Slot=0;Slot<DailyCount;++Slot)
    {
        FStableHorseOffer& Offer=Offers.AddDefaulted_GetRef();
        FGuid Id=FGuid::NewDeterministicGuid(Prefix+FString::FromInt(Slot));
        // Preserve R26 lot IDs, including its collision adjustment, so a sold lot stays sold after update.
        // The new birth name is rolled independently of this legacy allocation.
        while(UsedNames[Id.D%FStableHorseTraits::NameCount])++Id.D;
        UsedNames[Id.D%FStableHorseTraits::NameCount]=true;
        Offer.Horse.HorseId=Id;
        Offer.Horse.BirthVersion=FStableHorseTraits::IndependentRolls;
        Offer.Horse.ApplyBirthLimits();
        Offer.Price=Offer.Horse.BirthPrice();
    }
    return Offers;
}
