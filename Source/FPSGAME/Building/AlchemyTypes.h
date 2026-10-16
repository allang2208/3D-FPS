#pragma once
#include "CoreMinimal.h"
#include "AlchemyTypes.generated.h"

class APawn;

enum class EAlchemyOp : uint8 {Stop,Pour,Grind,Stir,Heat,Book,Timer,Bottle};

struct FAlchemyInput
{
    FString Item;
    int32 Count=1;
};
struct FAlchemyStep
{
    FString Id,Action,Item,Text;
    float Amount=1,MinHeat=0,MaxHeat=100;
    int32 Direction=1;
};
struct FAlchemyRecipe
{
    FName Id;
    int32 Version=1,BaseCount=2,BonusCount=1;
    bool AutoBase=false,FreeBrewing=false;
    float BottleHeat=40;
    FString Name,Output,Description,Raw;
    FLinearColor Color=FLinearColor(.02f,.3f,.7f);
    TArray<FAlchemyInput> Inputs;
    TArray<FAlchemyStep> Steps;
};

/** RPC-safe transport for one quantity; gameplay and saved jobs retain their maps. */
USTRUCT()
struct FColdSteelAlchemyNetQuantity
{
    GENERATED_BODY()
    UPROPERTY() FString Key;
    UPROPERTY() int64 Value=0;
};

/** Owner-only progress; payment, item templates and recipe snapshot travel with inventory receipts. */
USTRUCT()
struct FColdSteelAlchemyNetState
{
    GENERATED_BODY()
    UPROPERTY() FString JobId;
    UPROPERTY() int64 Revision=0;
    UPROPERTY() int64 InventoryRevision=0;
    UPROPERTY() TArray<float> Progress;
    UPROPERTY() TArray<FColdSteelAlchemyNetQuantity> Opened;
    UPROPERTY() TArray<FColdSteelAlchemyNetQuantity> Poured;
    UPROPERTY() TArray<FString> Faults;
    UPROPERTY() float Temperature=20;
    UPROPERTY() float Penalty=0;
    UPROPERTY() float ScorchSeconds=0;
    UPROPERTY() double Elapsed=0;
    UPROPERTY() bool Active=false;
    UPROPERTY() bool Bottling=false;
    UPROPERTY() bool TimerRunning=false;
    UPROPERTY() bool Saving=false;
    UPROPERTY() float ActionRemaining=0;
    UPROPERTY() float ServerTime=0;
    UPROPERTY() bool Finished=false;
    UPROPERTY() bool Passed=false;
    UPROPERTY() int32 OutputCount=0;
    UPROPERTY() uint8 Heat=0;
    UPROPERTY() FString Notice;
    UPROPERTY() FString Result;
};

/** Small public state. One cauldron is leased to a pawn while its private batch is active. */
USTRUCT()
struct FAlchemyBenchState
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<APawn> Operator=nullptr;
    UPROPERTY() FString JobId;
    UPROPERTY() FName Recipe;
    UPROPERTY() float Temperature=20;
    UPROPERTY() float Fill=0;
    UPROPERTY() FLinearColor Color=FLinearColor(.02f,.3f,.7f);
    UPROPERTY() uint8 Heat=0;
    UPROPERTY() uint8 Tool=0;
    UPROPERTY() int32 Ingredient=0;
    UPROPERTY() int32 ActionSerial=0;
    UPROPERTY() float ActionTime=0;
    UPROPERTY() float Stir=0;
    UPROPERTY() float StirPhase=0;
    UPROPERTY() float SampleTime=0;
    UPROPERTY() float InputEndTime=0;
    UPROPERTY() int32 BookPage=0;
    UPROPERTY() float TimerFraction=0;
    UPROPERTY() bool TimerRunning=false;
    UPROPERTY() bool HourglassInverted=false;
};
