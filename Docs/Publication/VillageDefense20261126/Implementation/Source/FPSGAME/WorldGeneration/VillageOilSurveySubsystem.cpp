#include "VillageOilSurveySubsystem.h"
#include "VillageHotOil.h"

bool UVillageOilSurveySubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{return Type==EWorldType::Game || Type==EWorldType::PIE;}

TStatId UVillageOilSurveySubsystem::GetStatId() const
{RETURN_QUICK_DECLARE_CYCLE_STAT(UVillageOilSurveySubsystem,STATGROUP_Tickables);}

void UVillageOilSurveySubsystem::Add(AVillageOilField* Field)
{Fields.AddUnique(Field);}

void UVillageOilSurveySubsystem::Remove(AVillageOilField* Field)
{Fields.Remove(Field);}

void UVillageOilSurveySubsystem::Tick(float Delta)
{
    // Keep link tests and shoreline bisection atomic (at most 10 traces each).
    // Rotate the first field as well, so simultaneous pours share the budget.
    int Remaining=384,Idle=0;
    while(Remaining>=10 && Idle<Fields.Num())
    {
        if(!Fields.IsValidIndex(Cursor))Cursor=0;
        auto* Field=Fields[Cursor].Get();
        if(!Field){Fields.RemoveAtSwap(Cursor);continue;}
        ++Cursor;
        const int Used=Field->SurveyStep(FMath::Min(Remaining,32));
        Remaining-=Used;
        Idle=Used?0:Idle+1;
    }
}
