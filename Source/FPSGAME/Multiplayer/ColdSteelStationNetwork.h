#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "ColdSteelStationNetwork.generated.h"
USTRUCT()
struct FColdSteelForgeNetState
{
    GENERATED_BODY()
    UPROPERTY() FString JobId;
    UPROPERTY() int32 Hits=0;
    UPROPERTY() bool Finished=false;
    UPROPERTY() TArray<FVector2D> Points;
    UPROPERTY() bool Active=false;
    UPROPERTY() bool Open=false;
    UPROPERTY() bool Pending=false;
    UPROPERTY() int32 Completed=0;
    UPROPERTY() double Elapsed=0;
    UPROPERTY() double Remaining=0;
    UPROPERTY() double ContactRemaining=0;
    UPROPERTY() double Window=0;
    UPROPERTY() float Life=0;
};
USTRUCT()
struct FColdSteelAssemblyNetState
{
    GENERATED_BODY()
    UPROPERTY() FString Id;
    UPROPERTY() int32 InstalledMask=0;
    UPROPERTY() TArray<float> Scores;
    UPROPERTY() TArray<int32> Misses;
    UPROPERTY() float CalibrationSeconds=0;
    UPROPERTY() float CalibrationTime=0;
    UPROPERTY() float CalibrationError=0;
    UPROPERTY() float Quality=0;
    UPROPERTY() bool Finished=false;
};
// Compressed on the existing profile envelope, then sent as paced owner-only chunks.
UCLASS()
class UColdSteelWoodNetState : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() FColdSteelWoodworkingJob Job;
    UPROPERTY() int64 InventoryRevision=0;
    UPROPERTY() FName Selected;
    UPROPERTY() uint8 Phase=0;
    UPROPERTY() uint8 Mode=0;
    UPROPERTY() bool Open=false;
    UPROPERTY() bool Motor=false;
    UPROPERTY() bool Feeding=false;
    UPROPERTY() bool UndoPoseValid=false;
    UPROPERTY() bool StrokeChanged=false;
    UPROPERTY() double Elapsed=0.;
    UPROPERTY() double ServerTime=0.;
    UPROPERTY() FVector2D Offset=FVector2D::ZeroVector;
    UPROPERTY() FVector2D StrokeOffset=FVector2D::ZeroVector;
    UPROPERTY() FVector2D UndoOffset=FVector2D::ZeroVector;
    UPROPERTY() double Angle=0.;
    UPROPERTY() double StrokeAngle=0.;
    UPROPERTY() double UndoAngle=0.;
    UPROPERTY() TArray<uint8> Mask;
    UPROPERTY() FString Notice;
};

namespace ColdSteelStationNet
{
    struct FInputScope {FInputScope();~FInputScope();bool Root;};
    bool IsClient(const UObject* Context);
    bool Request(const UObject* Context,const FString& Mode,FName Recipe=NAME_None,int64 Count=1,class AActor* Target=nullptr,FIntVector Cell=FIntVector::ZeroValue);
    void Input(const UObject* Context,FName System,uint8 Op,FName Recipe=NAME_None,int32 Index=0,FVector2D A=FVector2D::ZeroVector,FVector2D B=FVector2D::ZeroVector);
}
