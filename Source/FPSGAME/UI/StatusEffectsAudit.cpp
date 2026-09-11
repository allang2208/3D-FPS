#include "StatusEffectsAudit.h"
#include "StatusEffectsHUD.h"
#include "StatusEffectsComponent.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Blueprint/WidgetTree.h"
#include "Components/ScrollBox.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Monsters/PoisonMaggotProjectile.h"
#include "../Monsters/HandBrainFearComponent.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "HighResScreenshot.h"
#include "TimerManager.h"
#include "Framework/Application/SlateApplication.h"

void UStatusEffectsAudit::OnWorldBeginPlay(UWorld& W)
{Super::OnWorldBeginPlay(W);if(W.IsGameWorld()&&FParse::Param(FCommandLine::Get(),TEXT("StatusEffectsAudit"))){Began=W.GetTimeSeconds();W.GetTimerManager().SetTimer(Timer,this,&ThisClass::Step,.05f,true,4.f);}}
void UStatusEffectsAudit::Deinitialize(){if(GetWorld())GetWorld()->GetTimerManager().ClearTimer(Timer);Super::Deinitialize();}
void UStatusEffectsAudit::Check(const FString& N,bool P){(P?Passed:Failed).Add(N);UE_LOG(LogTemp,Display,TEXT("STATUS_ASSERT %s %s"),P?TEXT("PASS"):TEXT("FAIL"),*N);}
void UStatusEffectsAudit::Capture(const FString& N){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("StatusEffects")/(N+TEXT(".png")),true,false);}
void UStatusEffectsAudit::Finish()
{
 auto J=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> P,F;for(const auto& N:Passed)P.Add(MakeShared<FJsonValueString>(N));for(const auto& N:Failed)F.Add(MakeShared<FJsonValueString>(N));J->SetArrayField(TEXT("passed"),P);J->SetArrayField(TEXT("failed"),F);J->SetBoolField(TEXT("complete"),true);
 FString S;auto W=TJsonWriterFactory<>::Create(&S);FJsonSerializer::Serialize(J,W);FFileHelper::SaveStringToFile(S,*(FPaths::ProjectSavedDir()/TEXT("StatusEffects/acceptance.json")));UE_LOG(LogTemp,Display,TEXT("STATUS_AUDIT_COMPLETE failures=%d"),Failed.Num());GetWorld()->GetTimerManager().ClearTimer(Timer);FPlatformMisc::RequestExitWithStatus(false,Failed.IsEmpty()?0:1);
}
void UStatusEffectsAudit::Step()
{
 const double Now=GetWorld()->GetTimeSeconds(),T=Now-Started;if(Now-Began>45){Check(TEXT("completed_in_time"),false);Finish();return;}
 auto Next=[&](){++Stage;Started=Now;};
 if(Stage==0)
 {
  Player=UGameplayStatics::GetPlayerCharacter(this,0);HUD=GetWorld()->GetSubsystem<UStatusEffectsHUDSubsystem>()->GetHUD();for(TActorIterator<APoisonMaggotMonster> I(GetWorld());I;++I)Monster=*I;
  if(!Player.IsValid()||!HUD.IsValid()||!Monster.IsValid())return;
  auto* AI=Cast<AMonsterAIController>(Monster->GetController());if(!AI)return;AI->SetDecisionEnabled(false);for(TActorIterator<APoisonMaggotProjectile> I(GetWorld());I;++I)I->Destroy();Monster->SetState(EPoisonMaggotState::Idle);Monster->GetCharacterMovement()->StopMovementImmediately();
  Source=UStatusEffectsComponent::GetOrCreate(Player.Get());Check(TEXT("empty_bar_hidden"),HUD->VisibleEffectCount()==0);
  auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();BeforeHP=H->Health;
  auto* Poison=NewObject<UMaggotPoisonComponent>(Player.Get());Player->AddInstanceComponent(Poison);Poison->RegisterComponent();for(int32 I=0;I<3;++I)Poison->AddStack(Monster.Get());
  auto* Fear=NewObject<UHandBrainFearComponent>(Player.Get());Player->AddInstanceComponent(Fear);Fear->RegisterComponent();Fear->Apply(Monster.Get());Fear->Apply(Monster.Get());
  Source->SetTimed(TEXT("buff"),12);Source->SetPersistent(TEXT("shield"),TEXT("持续"));
  auto* PC=Cast<APlayerController>(Player->GetController());PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftAlt,IE_Pressed,1.f));Next();return;
 }
 if(Stage==1&&T>.35)
 {
  BeforeHP=Player->FindComponentByClass<UFPSCombatHealthComponent>()->Health;auto* P=HUD->TileFor(TEXT("poison"));auto* F=HUD->TileFor(TEXT("fear"));auto* B=HUD->TileFor(TEXT("buff"));auto* S=HUD->TileFor(TEXT("shield"));
  Check(TEXT("four_cards_from_live_poison_fear_and_display_records"),HUD->VisibleEffectCount()==4&&P&&F&&B&&S);
  Check(TEXT("live_poison_stack_decay_countdown"),P&&P->View.Stacks==3&&P->View.Remaining>4&&P->View.Duration==5);
  Check(TEXT("live_fear_stack_countdown"),F&&F->View.Stacks==2&&F->View.Remaining>2&&F->View.Duration==3);
  Check(TEXT("original_persistent_label"),S&&S->View.TimeText()==TEXT("持续"));
  if(P&&F)
  {
   const FVector2D Origin=FVector2D(P->GetCachedGeometry().GetAbsolutePosition())-FVector2D(HUD->GetCachedGeometry().GetAbsolutePosition());const FVector2D NextOrigin=FVector2D(F->GetCachedGeometry().GetAbsolutePosition())-FVector2D(HUD->GetCachedGeometry().GetAbsolutePosition());
   UE_LOG(LogTemp,Display,TEXT("STATUS_LAYOUT origin=%s size=%s next=%s"),*Origin.ToString(),*P->GetCachedGeometry().GetLocalSize().ToString(),*NextOrigin.ToString());
   Check(TEXT("original_104_12_position_54_44_tile_12_gap"),Origin.Equals({104,12},1)&&FVector2D(P->GetCachedGeometry().GetLocalSize()).Equals(FVector2D(54,44),1)&&FMath::IsNearlyEqual(NextOrigin.X-Origin.X,66.,1.));
   const FVector2D Point=P->GetCachedGeometry().LocalToAbsolute(FVector2D(27,22));
   FSlateApplication::Get().SetCursorPos(Point);
   FSlateApplication::Get().ProcessMouseMoveEvent(FPointerEvent(0,Point,Point-FVector2D(1,0),TSet<FKey>(),EKeys::Invalid,0,FModifierKeysState()));
  }
  Next();return;
 }
 if(Stage==2&&T>.4)
 {
  Check(TEXT("real_pointer_hover_opens_poison_tooltip"),HUD->IsTipVisible()&&HUD->TooltipType()==TEXT("poison"));
  Check(TEXT("tooltip_within_viewport"),HUD->TooltipPosition().X>=8&&HUD->TooltipPosition().Y>=8);
  Capture(TEXT("four-effects-hover"));Next();return;
 }
 if(Stage==3&&T>.3)
 {
  Source->SetTimed(TEXT("buff"),.5f,2);auto* B=HUD->TileFor(TEXT("buff"));Check(TEXT("refresh_merges_type_preserves_longer_duration"),HUD->VisibleEffectCount()==4&&B&&B->View.Stacks==2&&B->View.Remaining>9);
  Source->SetBattles(TEXT("slow"),2);Source->SetTimed(TEXT("stun"),1.5f);HUD->Refresh();
  Check(TEXT("overflow_and_battle_count"),HUD->VisibleEffectCount()==6&&HUD->TileFor(TEXT("slow"))->View.TimeText()==TEXT("2场"));
  Next();return;
 }
 if(Stage==4&&T>.2&&!Scrolled)
 {
  const FVector2D Point=HUD->TileFor(TEXT("poison"))->GetCachedGeometry().LocalToAbsolute(FVector2D(27,22));auto& App=FSlateApplication::Get();
  App.ProcessMouseMoveEvent(FPointerEvent(0,Point,Point-FVector2D(1,0),TSet<FKey>(),EKeys::Invalid,0,FModifierKeysState()));
  App.ProcessMouseWheelOrGestureEvent(FPointerEvent(0,Point,Point,TSet<FKey>(),EKeys::Invalid,-4,FModifierKeysState()),nullptr);Scrolled=true;return;
 }
 if(Stage==4&&T>.7&&!ScrollChecked)
 {
  TArray<UWidget*> Widgets;HUD->WidgetTree->GetAllWidgets(Widgets);bool Moved=false;for(auto* W:Widgets)if(auto* Scroll=Cast<UScrollBox>(W)){Moved=Scroll->GetScrollOffset()>1;Scroll->ScrollToStart();}
  Check(TEXT("real_mouse_wheel_reveals_overflow_row"),Moved);Source->Remove(TEXT("buff"));Source->SetBattles(TEXT("slow"),0);
  Cast<APlayerController>(Player->GetController())->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftAlt,IE_Released,0.f));ScrollChecked=true;return;
 }
 if(Stage==4&&T>4.3)
 {
  Check(TEXT("alt_release_hides_tooltip"),!HUD->IsTipVisible());HUD->Refresh();auto* P=HUD->TileFor(TEXT("poison"));Check(TEXT("expired_effects_removed"),!HUD->TileFor(TEXT("fear"))&&!HUD->TileFor(TEXT("stun"))&&!HUD->TileFor(TEXT("slow"))&&!HUD->TileFor(TEXT("buff")));
  Check(TEXT("poison_decay_updates_existing_tile"),P&&P->View.Stacks==2&&P->View.Remaining>3);
  Check(TEXT("poison_still_applies_real_damage"),Player->FindComponentByClass<UFPSCombatHealthComponent>()->Health<BeforeHP-10&&Player->FindComponentByClass<UMaggotPoisonComponent>()->TicksApplied>=5);
  Check(TEXT("fear_releases_movement_input"),!Player->GetController()->IsMoveInputIgnored());
  Capture(TEXT("poison-decay"));UGameplayStatics::ApplyDamage(Player.Get(),100000,Player->GetController(),Monster.Get(),UMaggotPoisonDamage::StaticClass());Next();return;
 }
 if(Stage==5&&T>.3){HUD->Refresh();Check(TEXT("death_hides_all_effects_and_tooltip"),HUD->VisibleEffectCount()==0&&!HUD->IsTipVisible());Next();return;}
 if(Stage==6&&T>2.3)
 {
  auto* NewPlayer=UGameplayStatics::GetPlayerCharacter(this,0);Check(TEXT("actual_respawn_rebinds_same_hud"),NewPlayer&&NewPlayer!=Player.Get()&&HUD.Get()==GetWorld()->GetSubsystem<UStatusEffectsHUDSubsystem>()->GetHUD()&&HUD->VisibleEffectCount()==0);
  auto* NewSource=UStatusEffectsComponent::GetOrCreate(NewPlayer);NewSource->SetTimed(TEXT("buff"),.3f);Check(TEXT("respawn_new_effect_appears"),HUD->TileFor(TEXT("buff"))!=nullptr);Next();return;
 }
 if(Stage==7&&T>.5){Check(TEXT("countdown_expiry_hides_empty_bar"),HUD->VisibleEffectCount()==0);Finish();}
}
