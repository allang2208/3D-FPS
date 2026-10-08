#include "SwordWaveTuning.h"
#include "../UI/ColdSteelEnhancementSystem.h"

SwordWaveTuning::FFlight SwordWaveTuning::RiftFlight(const UColdSteelEnhancementSystem* Enchant,const FColdSteelItem* Item)
{
    FFlight Flight;
    if(!Enchant)return Flight;
    double Range=12.,Speed=18.;
    if(const auto* Rule=Enchant->Scroll(TEXT("riftSlash"));Rule&&Rule->Effects.IsValid())
    {
        Rule->Effects->TryGetNumberField(TEXT("riftSlashRangeM"),Range);
        Rule->Effects->TryGetNumberField(TEXT("riftSlashSpeedM"),Speed);
    }
    if(Item&&Enchant->Effect(*Item,TEXT("riftSlash"))>0.)
    {
        Range=Enchant->Effect(*Item,TEXT("riftSlashRangeM"),Range);
        Speed=Enchant->Effect(*Item,TEXT("riftSlashSpeedM"),Speed);
    }
    Flight.RangeCM=FMath::Max(1.f,float(Range*100.));Flight.SpeedCM=FMath::Max(1.f,float(Speed*100.));
    return Flight;
}
