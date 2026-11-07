#pragma once
#include "CoreMinimal.h"
class AFPSGAMECharacter;
class UColdSteelStatusModel;
struct FColdSteelProfile;
namespace HighlandEquipmentWire
{
bool Enabled();
FColdSteelProfile Seed(UColdSteelStatusModel* Model,bool Host);
void Select(FColdSteelProfile& State,int32 Phase,bool Host);
bool Check(AFPSGAMECharacter* Pawn,int32 Phase,bool Host,FString& Details);
void PlaceTarget(AFPSGAMECharacter* Pawn,bool Lethal);
bool TickGaleAttack(AFPSGAMECharacter* Pawn,int32 Phase);
void ObserveJudgment(AFPSGAMECharacter* Pawn);
bool TickCharge(AFPSGAMECharacter* Pawn,int32 Phase);
}
