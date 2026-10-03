#include "HangingBellM09.h"
#include "MonsterAIController.h"
#include "BrainComponent.h"
#include "../SceneTestPortal.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
void AHangingBellM09::ConfigureReturnPortal(AActor* Portal)
{
 if(auto* Door=Cast<ASceneTestPortal>(Portal))Door->Configure(TEXT("/Game/GameMaps/DayNight_Lighting"),TEXT("RETURN TO HUB"));
}
#if !UE_BUILD_SHIPPING
namespace M09Development
{
void Message(const FString& Text)
{
 UE_LOG(LogTemp,Display,TEXT("M09: %s"),*Text);
 if(GEngine)GEngine->AddOnScreenDebugMessage(-1,6.f,FColor::Cyan,Text);
}
AHangingBellM09* Nearest(UWorld* World)
{
 if(!World||World->GetNetMode()==NM_Client)return nullptr;
 APawn* Player=UGameplayStatics::GetPlayerPawn(World,0);if(!Player)return nullptr;
 AHangingBellM09* Best=nullptr;double Distance=DBL_MAX;
 for(TActorIterator<AHangingBellM09> It(World);It;++It)
 {
  const double D=FVector::DistSquared(It->GetActorLocation(),Player->GetActorLocation());
  if(!It->Dead()&&D<Distance){Distance=D;Best=*It;}
 }
 return Best;
}
FAutoConsoleCommandWithWorldAndArgs Room(TEXT("m09.TestRoom"),TEXT("Travel to the saved M09 ceiling test room."),
 FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&,UWorld* W){
  if(W&&W->IsGameWorld()&&W->GetNetMode()!=NM_Client)UGameplayStatics::OpenLevel(W,TEXT("/Game/Tests/HangingBellM09/L_M09CeilingTest"));
 }));
FAutoConsoleCommandWithWorldAndArgs Hub(TEXT("m09.Hub"),TEXT("Return to the main hub."),
 FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&,UWorld* W){
  if(W&&W->IsGameWorld()&&W->GetNetMode()!=NM_Client)UGameplayStatics::OpenLevel(W,TEXT("/Game/GameMaps/DayNight_Lighting"));
 }));
FAutoConsoleCommandWithWorldAndArgs AI(TEXT("m09.AI"),TEXT("m09.AI 0|1: pause/resume the nearest living M09 brain."),
 FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args,UWorld* W){
  auto* M=Nearest(W);if(!M||Args.IsEmpty()){Message(TEXT("Spawn M09 under its authored ceiling, then use m09.AI 0 or 1."));return;}
  const bool Enable=Args[0]!=TEXT("0");M->StopCeiling();
  if(auto* C=Cast<AMonsterAIController>(M->GetController()))if(C->BrainComponent)
  {
   if(Enable)C->BrainComponent->ResumeLogic(TEXT("M09 manual control finished"));
   else C->BrainComponent->PauseLogic(TEXT("M09 manual attack control"));
   Message(Enable?TEXT("Nearest M09 AI resumed."):TEXT("Nearest M09 AI paused; current attack finishes."));
  }
 }));
FAutoConsoleCommandWithWorldAndArgs Attack(TEXT("m09.Attack"),TEXT("Nearest M09: SwingLeft, SwingRight, Resonance, Gaze, Claw, Stagger, Death."),
 FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args,UWorld* W){
  auto* M=Nearest(W);if(!M||Args.IsEmpty()){Message(TEXT("m09.Attack SwingLeft|SwingRight|Resonance|Gaze|Claw|Stagger|Death"));return;}
  Message(M->TriggerAttack(FName(*Args[0]))?TEXT("M09 action started."):TEXT("No action: check its name and clear line of sight."));
 }));
FAutoConsoleCommandWithWorldAndArgs Drop(TEXT("m09.Drop"),TEXT("Release and kill the nearest living M09."),
 FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&,UWorld* W){
  if(auto* M=Nearest(W))M->TriggerAttack(TEXT("Death"));
 }));
}
#endif
