#include "StatusEffectsComponent.h"
#include "../Monsters/PoisonMaggotProjectile.h"
#include "../Monsters/HandBrainFearComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Combat/ProgressiveInfectionComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

FString FStatusEffectView::TimeText() const
{
 if(Type==TEXT("fountainBlessing"))
 {const int32 Seconds=FMath::CeilToInt(FMath::Max(0.f,Remaining));return FString::Printf(TEXT("%d:%02d"),Seconds/60,Seconds%60);}
 return Persistent?(DurationText.IsEmpty()?TEXT("持续"):DurationText):Battles>=0?FString::Printf(TEXT("%d场"),Battles):FString::Printf(TEXT("%ds"),FMath::CeilToInt(FMath::Max(0.f,Remaining)));
}
FStatusEffectView UStatusEffectsComponent::Definition(FName Type)
{
 static TMap<FName,FStatusEffectView> Catalog;
 if(Catalog.IsEmpty())
 {
  FString Text;TSharedPtr<FJsonObject> Json;
  if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/status_effects.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Json))
   for(const auto& Value:Json->GetArrayField(TEXT("effects"))){const auto O=Value->AsObject();FStatusEffectView V;V.Type=FName(O->GetStringField(TEXT("type")));V.Icon=O->GetStringField(TEXT("icon"));V.Name=O->GetStringField(TEXT("name"));V.Description=O->GetStringField(TEXT("description"));V.Kind=FName(O->GetStringField(TEXT("kind")));V.Group=FName(O->GetStringField(TEXT("group")));V.Color=FLinearColor::FromSRGBColor(FColor::FromHex(O->GetStringField(TEXT("color"))));Catalog.Add(V.Type,V);}
 }
 if(const auto* Found=Catalog.Find(Type))return *Found;FStatusEffectView V;V.Type=Type;V.Name=Type.ToString();V.Icon=TEXT("?");return V;
}
void UStatusEffectsComponent::AllDefinitions(TArray<FStatusEffectView>& Out)
{
 // 全量目录（单一事实源）：与 Definition 相同的解析口径，进程内只读一次文件，
 // 按显示名稳定排序，供图鉴状态栏列表使用；HUD 不消费本接口。
 static TArray<FStatusEffectView> Sorted;
 if(Sorted.IsEmpty())
 {
  FString Text;TSharedPtr<FJsonObject> Json;
  if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/status_effects.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Json))
   for(const auto& Value:Json->GetArrayField(TEXT("effects"))){const auto O=Value->AsObject();FStatusEffectView V;V.Type=FName(O->GetStringField(TEXT("type")));V.Icon=O->GetStringField(TEXT("icon"));V.Name=O->GetStringField(TEXT("name"));V.Description=O->GetStringField(TEXT("description"));V.Kind=FName(O->GetStringField(TEXT("kind")));V.Group=FName(O->GetStringField(TEXT("group")));V.Color=FLinearColor::FromSRGBColor(FColor::FromHex(O->GetStringField(TEXT("color"))));Sorted.Add(V);}
  Sorted.Sort([](const FStatusEffectView& A,const FStatusEffectView& B){return A.Name<B.Name;});
 }
 Out=Sorted;
}
bool UStatusEffectsComponent::HasType(FName Type)
{if(Type.IsNone())return false;const FStatusEffectView V=Definition(Type);return !(V.Icon==TEXT("?")&&V.Type==Type&&V.Description.IsEmpty());}
UStatusEffectsComponent* UStatusEffectsComponent::GetOrCreate(AActor* Owner)
{if(!Owner)return nullptr;if(auto* C=Owner->FindComponentByClass<UStatusEffectsComponent>())return C;auto* C=NewObject<UStatusEffectsComponent>(Owner);Owner->AddInstanceComponent(C);C->RegisterComponent();return C;}
void UStatusEffectsComponent::Notify(AActor* Owner){if(auto* C=GetOrCreate(Owner))C->OnChanged.Broadcast();}
TArray<FStatusEffectView> UStatusEffectsComponent::Snapshot() const
{
 TArray<FStatusEffectView> Result;if(auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>())if(H->IsDead())return Result;
 if(const auto* Survival=GetOwner()->FindComponentByClass<UFPSSurvivalComponent>())
 {
  const auto State=Survival->GetState();
  if(State.FountainBlessingSeconds>0.f)
  {auto V=Definition(TEXT("fountainBlessing"));V.Duration=FFPSSurvivalState::FountainBlessingDuration;V.Remaining=State.FountainBlessingSeconds;Result.Add(V);}
  if(State.IsSanityDepleted())
  {auto V=Definition(TEXT("sanityCollapse"));V.Persistent=true;V.DurationText=TEXT("恢复 SAN 后解除");Result.Add(V);}
 }
 if(const auto* Pawn=Cast<APawn>(GetOwner());Pawn&&Pawn->IsPlayerControlled())
  if(const auto* Run=UDungeonRunSubsystem::Get(GetWorld());Run&&!Run->ActiveShrineBlessing().IsNone())
  {auto V=Definition(Run->ActiveShrineBlessing());V.Persistent=true;V.DurationText=TEXT("本次地牢");Result.Add(V);}
 if(auto* P=GetOwner()->FindComponentByClass<UMaggotPoisonComponent>())if(P->Stacks>0){auto V=Definition(TEXT("poison"));V.Stacks=P->Stacks;V.Duration=5;V.Remaining=P->GetDecayRemaining();V.Description+=TEXT(" 每 5 秒消退 1 层；倒计时为下一次减层时间。");Result.Add(V);}
 if(auto* F=GetOwner()->FindComponentByClass<UHandBrainFearComponent>())if(F->Stacks>0){auto V=Definition(TEXT("fear"));V.Stacks=F->Stacks;V.Duration=3;V.Remaining=F->GetRemainingSeconds();Result.Add(V);}
 if(const auto* Infection=GetOwner()->FindComponentByClass<UProgressiveInfectionComponent>();Infection&&Infection->GetState().bActive)
 {
  const auto& State=Infection->GetState();const auto Stage=State.Stage();auto V=Definition(TEXT("infection"));
  const TCHAR* StageName=Stage==EInfectionStage::Early?TEXT("初期"):Stage==EInfectionStage::Middle?TEXT("中期"):TEXT("后期");
  V.Name=FString::Printf(TEXT("感染·%s"),StageName);V.Persistent=true;
  const float Middle=FMath::Max(1.f,State.Tuning.MiddleAtSeconds),Late=FMath::Max(Middle+1.f,State.Tuning.LateAtSeconds);
  const float Next=Stage==EInfectionStage::Early?Middle:Late;
  V.DurationText=Stage==EInfectionStage::Late?TEXT("持续至治愈"):FString::Printf(TEXT("%ds恶化"),FMath::CeilToInt(FMath::Max(0.f,Next-State.ElapsedSeconds)));
  V.Description=FString::Printf(TEXT("%s：每秒损失当前最大生命值的 %.2f%%，六维属性降低 %.0f%%。重复感染不叠加、不重置恶化时间；净化可治愈。"),StageName,State.HealthLossRatio()*100.f,(1.f-State.AttributeMultiplier())*100.f);
  Result.Add(V);
 }
 const double Now=GetWorld()->GetTimeSeconds();
 for(const auto& R:Records){auto V=R.View;if(!V.Persistent&&V.Battles<0){V.Remaining=FMath::Max(0.f,float(R.End-Now));if(V.Remaining<=0)continue;}if(V.Battles==0)continue;if(!Result.ContainsByPredicate([&](const auto& E){return E.Type==V.Type;}))Result.Add(V);}
 return Result;
}
void UStatusEffectsComponent::SetTimed(FName Type,float Seconds,int32 Stacks)
{SetTimedDisplay(Type,Seconds,Stacks,FString(),FString(),FString());}
void UStatusEffectsComponent::SetTimedDisplay(FName Type,float Seconds,int32 Stacks,const FString& Name,const FString& Icon,const FString& ColorHex)
{
 if(Seconds<=0){Remove(Type);return;}const double Now=GetWorld()->GetTimeSeconds();FRecord* R=Records.FindByPredicate([&](const auto& E){return E.View.Type==Type;});if(!R){Records.AddDefaulted();R=&Records.Last();R->View=Definition(Type);}
 const bool WasTimed=!R->View.Persistent&&R->View.Battles<0;R->End=WasTimed?FMath::Max(R->End,Now+Seconds):Now+Seconds;R->View.Duration=WasTimed?FMath::Max(R->View.Duration,Seconds):Seconds;R->View.Persistent=false;R->View.Battles=-1;R->View.Stacks=Stacks;
 if(!Name.IsEmpty())R->View.Name=Name;if(!Icon.IsEmpty())R->View.Icon=Icon;if(!ColorHex.IsEmpty())R->View.Color=FLinearColor::FromSRGBColor(FColor::FromHex(ColorHex));
 OnChanged.Broadcast();
}
void UStatusEffectsComponent::SetPersistent(FName Type,const FString& Text,int32 Stacks)
{Records.RemoveAll([&](const auto& R){return R.View.Type==Type;});FRecord R;R.View=Definition(Type);R.View.Persistent=true;R.View.DurationText=Text;R.View.Stacks=Stacks;Records.Add(R);OnChanged.Broadcast();}
void UStatusEffectsComponent::SetBattles(FName Type,int32 Battles,int32 Stacks)
{Records.RemoveAll([&](const auto& R){return R.View.Type==Type;});if(Battles>0){FRecord R;R.View=Definition(Type);R.View.Battles=Battles;R.View.Stacks=Stacks;Records.Add(R);}OnChanged.Broadcast();}
void UStatusEffectsComponent::Remove(FName Type){Records.RemoveAll([&](const auto& R){return R.View.Type==Type;});OnChanged.Broadcast();}
void UStatusEffectsComponent::Clear(){Records.Empty();OnChanged.Broadcast();}
