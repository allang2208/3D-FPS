#pragma once
#include "RuneboundReviewAudit.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Production/RuneboundHammerTuning.h"
#include "../Combat/CombatStatusFormula.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace RuneboundReview
{
inline bool WireEnabled(){return FParse::Param(FCommandLine::Get(),TEXT("RuneboundReviewWire"));}
inline FColdSteelProfile Seed(UColdSteelStatusModel* Model,const FString& Instance,const FString& Head,const FString& Rune=TEXT(""))
{
    auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.Stamina=100;State.bSprintExhausted=false;State.DungeonRun={};
    for(auto& Skill:State.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
    auto Item=Model->CreateItem(RuneboundHammer::Definition);Item.InstanceId=Instance;Item.Place=1;Item.Cell=6;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
    if(!Data)Data=MakeShared<FJsonObject>();
    auto Parts=MakeShared<FJsonObject>();if(!Head.IsEmpty())Parts->SetStringField(TEXT("hammer_heads"),Head);
    if(!Rune.IsEmpty())Parts->SetStringField(TEXT("rune"),Rune);
    Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    State.Items={Item};return State;
}
inline void Freeze(AFPSGAMECharacter* Pawn)
{
    Pawn->SetActorTickEnabled(false);Pawn->GetCharacterMovement()->DisableMovement();Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    for(auto* Component:Pawn->GetComponents())Component->SetComponentTickEnabled(false);
}
inline FHitResult Hit(ARuneboundReviewTarget* Target)
{
    FHitResult H(Target,Target->GetCapsuleComponent(),Target->GetActorLocation(),FVector::UpVector);
    H.ImpactPoint=Target->GetActorLocation();H.bBlockingHit=true;return H;
}
inline void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Passed,const TCHAR* Role,const FString& Path)
{
    auto Report=MakeShared<FJsonObject>();Report->SetStringField(TEXT("role"),Role);Report->SetBoolField(TEXT("passed"),Passed);
    Report->SetArrayField(TEXT("checks"),Rows);Report->SetBoolField(TEXT("user_profile_modified"),false);
    Report->SetBoolField(TEXT("rendered"),false);Report->SetBoolField(TEXT("enemy_fixture_records_raw_damage"),true);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Path);
}
inline void Check(TArray<TSharedPtr<FJsonValue>>& Rows,bool& Passed,bool OK,const FString& Name)
{
    auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),OK);
    Rows.Add(MakeShared<FJsonValueObject>(R));Passed&=OK;UE_LOG(LogTemp,Display,TEXT("RUNEBOUND_REVIEW %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
}
}
