#include "StatusEffectsComponent.h"
#include "../Monsters/PoisonMaggotProjectile.h"
#include "../Monsters/HandBrainFearComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

FString FStatusEffectView::TimeText() const
{return Persistent?(DurationText.IsEmpty()?TEXT("持续"):DurationText):Battles>=0?FString::Printf(TEXT("%d场"),Battles):FString::Printf(TEXT("%ds"),FMath::CeilToInt(FMath::Max(0.f,Remaining)));}
FStatusEffectView UStatusEffectsComponent::Definition(FName Type)
{
 static TMap<FName,FStatusEffectView> Catalog;
 if(Catalog.IsEmpty())
 {
  FString Text;TSharedPtr<FJsonObject> Json;
  if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/status_effects.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Json))
   for(const auto& Value:Json->GetArrayField(TEXT("effects"))){const auto O=Value->AsObject();FStatusEffectView V;V.Type=FName(O->GetStringField(TEXT("type")));V.Icon=O->GetStringField(TEXT("icon"));V.Name=O->GetStringField(TEXT("name"));V.Description=O->GetStringField(TEXT("description"));V.Color=FLinearColor::FromSRGBColor(FColor::FromHex(O->GetStringField(TEXT("color"))));Catalog.Add(V.Type,V);}
 }
 if(const auto* Found=Catalog.Find(Type))return *Found;FStatusEffectView V;V.Type=Type;V.Name=Type.ToString();V.Icon=TEXT("?");return V;
}
UStatusEffectsComponent* UStatusEffectsComponent::GetOrCreate(AActor* Owner)
{if(!Owner)return nullptr;if(auto* C=Owner->FindComponentByClass<UStatusEffectsComponent>())return C;auto* C=NewObject<UStatusEffectsComponent>(Owner);Owner->AddInstanceComponent(C);C->RegisterComponent();return C;}
void UStatusEffectsComponent::Notify(AActor* Owner){if(auto* C=GetOrCreate(Owner))C->OnChanged.Broadcast();}
TArray<FStatusEffectView> UStatusEffectsComponent::Snapshot() const
{
 TArray<FStatusEffectView> Result;if(auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>())if(H->IsDead())return Result;
 if(auto* P=GetOwner()->FindComponentByClass<UMaggotPoisonComponent>())if(P->Stacks>0){auto V=Definition(TEXT("poison"));V.Stacks=P->Stacks;V.Duration=5;V.Remaining=P->GetDecayRemaining();V.Description+=TEXT(" 每 5 秒消退 1 层；倒计时为下一次减层时间。");Result.Add(V);}
 if(auto* F=GetOwner()->FindComponentByClass<UHandBrainFearComponent>())if(F->Stacks>0){auto V=Definition(TEXT("fear"));V.Stacks=F->Stacks;V.Duration=3;V.Remaining=F->GetRemainingSeconds();Result.Add(V);}
 const double Now=GetWorld()->GetTimeSeconds();
 for(const auto& R:Records){auto V=R.View;if(!V.Persistent&&V.Battles<0){V.Remaining=FMath::Max(0.f,float(R.End-Now));if(V.Remaining<=0)continue;}if(V.Battles==0)continue;if(!Result.ContainsByPredicate([&](const auto& E){return E.Type==V.Type;}))Result.Add(V);}
 return Result;
}
void UStatusEffectsComponent::SetTimed(FName Type,float Seconds,int32 Stacks)
{
 if(Seconds<=0){Remove(Type);return;}const double Now=GetWorld()->GetTimeSeconds();FRecord* R=Records.FindByPredicate([&](const auto& E){return E.View.Type==Type;});if(!R){Records.AddDefaulted();R=&Records.Last();R->View=Definition(Type);}
 const bool WasTimed=!R->View.Persistent&&R->View.Battles<0;R->End=WasTimed?FMath::Max(R->End,Now+Seconds):Now+Seconds;R->View.Duration=WasTimed?FMath::Max(R->View.Duration,Seconds):Seconds;R->View.Persistent=false;R->View.Battles=-1;R->View.Stacks=Stacks;OnChanged.Broadcast();
}
void UStatusEffectsComponent::SetPersistent(FName Type,const FString& Text,int32 Stacks)
{Records.RemoveAll([&](const auto& R){return R.View.Type==Type;});FRecord R;R.View=Definition(Type);R.View.Persistent=true;R.View.DurationText=Text;R.View.Stacks=Stacks;Records.Add(R);OnChanged.Broadcast();}
void UStatusEffectsComponent::SetBattles(FName Type,int32 Battles,int32 Stacks)
{Records.RemoveAll([&](const auto& R){return R.View.Type==Type;});if(Battles>0){FRecord R;R.View=Definition(Type);R.View.Battles=Battles;R.View.Stacks=Stacks;Records.Add(R);}OnChanged.Broadcast();}
void UStatusEffectsComponent::Remove(FName Type){Records.RemoveAll([&](const auto& R){return R.View.Type==Type;});OnChanged.Broadcast();}
void UStatusEffectsComponent::Clear(){Records.Empty();OnChanged.Broadcast();}
