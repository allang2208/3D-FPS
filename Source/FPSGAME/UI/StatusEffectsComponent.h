#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "StatusEffectsComponent.generated.h"

struct FStatusEffectView
{
 FName Type;FString Icon,Name,Description,DurationText;
 /** 增益/减益分类（目录 kind 字段：buff/debuff）；图鉴状态栏用，HUD 不消费。 */
 FName Kind;
 /** 来源分组（目录 group 字段：combat/triggered/persistent/tribute/dungeon_event）。 */
 FName Group;
 FLinearColor Color=FLinearColor(.5f,.5f,.4f);
 float Remaining=0,Duration=0;int32 Stacks=-1,Battles=-1;bool Persistent=false;
 FString TimeText() const;
};
DECLARE_MULTICAST_DELEGATE(FStatusEffectsChanged);

/** Read-only adapters for live poison/fear plus display records owned by other effects. */
UCLASS(ClassGroup=(UI),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UStatusEffectsComponent : public UActorComponent
{
 GENERATED_BODY()
public:
 static UStatusEffectsComponent* GetOrCreate(AActor* Owner);
 /** 目录探测：该 type 在 status_effects.json 中有正式条目（区别于 Definition 的 "?" 回退）。 */
 static bool HasType(FName Type);
 /** 全量目录（status_effects.json 逐条，含 kind 分类）：图鉴状态栏的唯一数据源，与 HUD 同源。 */
 static void AllDefinitions(TArray<FStatusEffectView>& Out);
 static void Notify(AActor* Owner);
 TArray<FStatusEffectView> Snapshot() const;
 FStatusEffectsChanged OnChanged;
 UFUNCTION(BlueprintCallable,Category="Status Display") void SetTimed(FName Type,float Seconds,int32 Stacks=-1);
 /** 同类型刷新取较长剩余；Name/Icon/ColorHex 非空时覆盖目录显示（旧「致残」借用 slow 计时但显示 🦴）。 */
 UFUNCTION(BlueprintCallable,Category="Status Display") void SetTimedDisplay(FName Type,float Seconds,int32 Stacks,const FString& Name,const FString& Icon,const FString& ColorHex);
 UFUNCTION(BlueprintCallable,Category="Status Display") void SetPersistent(FName Type,const FString& DurationText=TEXT("持续"),int32 Stacks=-1);
 UFUNCTION(BlueprintCallable,Category="Status Display") void SetBattles(FName Type,int32 RemainingBattles,int32 Stacks=-1);
 UFUNCTION(BlueprintCallable,Category="Status Display") void Remove(FName Type);
 UFUNCTION(BlueprintCallable,Category="Status Display") void Clear();
private:
 struct FRecord {FStatusEffectView View;double End=0;};
 TArray<FRecord> Records;
 static FStatusEffectView Definition(FName Type);
};
