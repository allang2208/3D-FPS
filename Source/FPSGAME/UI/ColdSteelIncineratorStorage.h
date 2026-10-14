#pragma once
#include "CoreMinimal.h"
#include "ColdSteelInventoryTypes.h"
class UColdSteelStatusModel;

namespace ColdSteelIncineratorStorage
{
    inline bool IsContainer(const FString& Key){return Key.StartsWith(TEXT("incinerator."));}
    struct FProduct { FString Item; int64 Count=0; };
    struct FRecipe { FString Input; int64 InputCount=1; TArray<FProduct> Outputs; };
    struct FRules
    {
        bool bValid=false,bAllowUnconfigured=false;
        FString Signature,Error;
        TArray<FRecipe> Recipes;
    };
    struct FQuote
    {
        bool bValid=false;
        int64 Generation=0;
        FString Container,RuleSignature,Reason;
        TArray<FColdSteelItem> Inputs;
        TArray<FProduct> Products;
        TArray<FString> Unconfigured;
    };
    FPSGAME_API FRules ParseRules(const FString& Json);
    FPSGAME_API FRules LoadRules();
    FPSGAME_API bool HasInputs(const FColdSteelProfile& State,const FString& Container=FString());
    FPSGAME_API FQuote Quote(const FColdSteelProfile& State,const FString& Container,const FRules& Rules);
    FPSGAME_API bool Prepare(UColdSteelStatusModel& Model,const FQuote& Quote,const FRules& Rules,FColdSteelProfile& Next,FString& Reason);
    FPSGAME_API bool DepositAmmo(UColdSteelStatusModel& Model,const FString& Ammo,int64 Count,FString& Reason,int32 Cell=-1);
    /** Partial retrieval is intentional: each blocked item stays in its original container; one final save. */
    FPSGAME_API bool Retrieve(UColdSteelStatusModel& Model,const FString& Container,FString& Reason);
    FPSGAME_API FString Describe(const FQuote& Quote,const UColdSteelStatusModel& Model,bool Confirmation);
    class FPSGAME_API FSession
    {
    public:
        FQuote Draft;
        bool Review(UColdSteelStatusModel& Model,const FString& Container,const FRules& Rules);
        bool Confirm(UColdSteelStatusModel& Model,const FRules& Rules,FString& Reason);
        void Cancel(){Draft=FQuote();}
    };
}
