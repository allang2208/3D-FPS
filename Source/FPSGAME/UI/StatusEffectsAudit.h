#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "StatusEffectsAudit.generated.h"
class ACharacter;class APoisonMaggotMonster;class UStatusEffectsComponent;class UStatusEffectsHUD;
UCLASS()
class FPSGAME_API UStatusEffectsAudit : public UWorldSubsystem
{
 GENERATED_BODY()
public:
 virtual void OnWorldBeginPlay(UWorld& World) override;
 virtual void Deinitialize() override;
private:
 void Step();void Check(const FString& Name,bool Pass);void Capture(const FString& Name);void Finish();
 FTimerHandle Timer;int32 Stage=0;double Began=0,Started=0;float BeforeHP=0;bool Scrolled=false,ScrollChecked=false;
 TWeakObjectPtr<ACharacter> Player;TWeakObjectPtr<APoisonMaggotMonster> Monster;
 TWeakObjectPtr<UStatusEffectsComponent> Source;TWeakObjectPtr<UStatusEffectsHUD> HUD;
 TArray<FString> Passed,Failed;
};
