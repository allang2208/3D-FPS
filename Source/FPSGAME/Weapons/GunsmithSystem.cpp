#include "GunsmithSystem.h"
#include "M4DrumReloadTiming.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace {
double Num(const TSharedPtr<FJsonObject>& O,const TCHAR* K,double Default=0){double V=Default;O->TryGetNumberField(K,V);return V;}
TArray<FString> Strings(const TSharedPtr<FJsonObject>& O,const TCHAR* K){TArray<FString> R;for(const auto& V:O->GetArrayField(K))R.Add(V->AsString());return R;}
FString Part(const FGunsmithParts& P,const FString& S){const FString* V=P.Find(S);return V?*V:TEXT("false");}
}
void UGunsmithSystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);Collection.InitializeDependency<UColdSteelStatusModel>();
    FString Text;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/gunsmith.json")))||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Catalog)){UE_LOG(LogTemp,Error,TEXT("Gunsmith catalog unavailable"));return;}
    SlotKeys=Strings(Catalog,TEXT("slots"));CategoryNames=Strings(Catalog,TEXT("categories"));DefaultNames=Strings(Catalog,TEXT("defaults"));
    for(const auto& V:Catalog->GetArrayField(TEXT("weapons"))){
        const auto O=V->AsObject();FGunsmithWeapon W;W.Source=O;
        W.Id=O->GetStringField(TEXT("id"));W.Model=O->GetStringField(TEXT("model"));W.Name=O->GetStringField(TEXT("name"));W.Allowed=Strings(O,TEXT("allowed"));
        const auto B=O->GetObjectField(TEXT("base"));W.Ammo=B->GetStringField(TEXT("ammo_item_id"));
        W.Base.ADS=FMath::Loge(20.)/Num(B,TEXT("ads_smooth"),9.98577424518);W.Base.Capacity=Num(B,TEXT("mag_size"),30);
        W.Base.Recoil=Num(B,TEXT("recoil"),100);W.Base.Shake=Num(B,TEXT("camera_shake"),100);W.Base.Interval=Num(B,TEXT("fire_interval"),.13);
        W.Base.Reload=Num(B,TEXT("reload_time"),1.5);W.Base.EmptyReload=Num(B,TEXT("empty_reload_time"));if(W.Base.EmptyReload<=0)W.Base.EmptyReload=W.Base.Reload;
        W.Base.Damage=Num(B,TEXT("damage"),25);W.Base.Speed=Num(B,TEXT("bullet_speed"),90);W.Base.Range=Num(B,TEXT("effective_range"),40);
        for(const auto& S:O->GetObjectField(TEXT("options"))->Values){TArray<FGunsmithOption> Options;
            for(const auto& Entry:S.Value->AsArray()){const auto P=Entry->AsObject();FGunsmithOption A;A.Id=P->GetStringField(TEXT("id"));A.Name=P->GetStringField(TEXT("name"));A.Description=P->GetStringField(TEXT("description"));
                for(const auto& E:P->GetArrayField(TEXT("effects")))A.Effects.Emplace(E->AsObject()->GetStringField(TEXT("text")),Num(E->AsObject(),TEXT("benefit")));
                const auto T=P->GetObjectField(TEXT("stats"));A.ADS=Num(T,TEXT("ads_percent"));A.Recoil=Num(T,TEXT("recoil_mult"),1);A.Shake=Num(T,TEXT("shake_mult"),1);
                A.Speed=Num(T,TEXT("bullet_speed_mult"),1);A.Interval=Num(T,TEXT("fire_interval_mult"),1);A.Spread=Num(T,TEXT("hip_spread_mult"),1);A.Range=Num(T,TEXT("range_mult"),1);A.Reload=Num(T,TEXT("reload_mult"),1);A.Magazine=Num(T,TEXT("mag_delta"));Options.Add(A);
            }W.Options.Add(FString(*S.Key),Options);
        }Weapons.Add(W.Id,W);
    }
}
void UGunsmithSystem::Deinitialize(){Close();Super::Deinitialize();}
const FGunsmithWeapon* UGunsmithSystem::Weapon(const FString& D)const{return Weapons.Find(D);}
const FGunsmithOption* UGunsmithSystem::Option(const FString& D,const FString& S,const FString& Id)const{const auto* W=Weapon(D);if(!W)return nullptr;const auto* A=W->Options.Find(S);return A?A->FindByPredicate([&](const auto& V){return V.Id==Id;}):nullptr;}
FGunsmithParts UGunsmithSystem::Normalize(const FString& D,const FGunsmithParts& Input)const
{
    FGunsmithParts Result;for(const auto& P:Input){FString Id=P.Value;if(P.Key==TEXT("stock")&&Id==TEXT("true"))Id=TEXT("compact");if(Id!=TEXT("false")&&Option(D,P.Key,Id))Result.Add(P.Key,Id);}return Result;
}
FGunsmithParts UGunsmithSystem::Installed(const FColdSteelItem& I)const
{
    FGunsmithParts P;TSharedPtr<FJsonObject> O;const TSharedPtr<FJsonObject>* Parts=nullptr;
    if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),O)&&O->TryGetObjectField(TEXT("gunsmith_parts"),Parts))for(const auto& Pair:(*Parts)->Values){FString Value;if(Pair.Value->Type==EJson::Boolean)Value=Pair.Value->AsBool()?TEXT("true"):TEXT("false");else if(Pair.Value->Type==EJson::String)Value=Pair.Value->AsString();P.Add(FString(*Pair.Key),Value);}
    return Normalize(I.Definition,P);
}
FGunsmithStats UGunsmithSystem::Calculate(const FString& D,const FGunsmithParts& P)const
{
    const auto* W=Weapon(D);if(!W)return {};auto R=W->Base;
    for(const auto& Pair:Normalize(D,P)){const auto& A=*Option(D,Pair.Key,Pair.Value);R.ADSPercent+=A.ADS;R.RecoilMultiplier*=A.Recoil;R.ShakeMultiplier*=A.Shake;R.Capacity+=A.Magazine;R.Interval*=A.Interval;R.Reload*=A.Reload;R.EmptyReload*=A.Reload;R.Speed*=A.Speed;R.Range*=A.Range;R.Spread*=A.Spread;++R.ActiveParts;}
    if(D==TEXT("ue_m4a1")&&Part(Normalize(D,P),TEXT("magazine"))==TEXT("large_drum"))
    {R.Reload*=M4DrumReloadTiming::NormalDurationScale;R.EmptyReload*=M4DrumReloadTiming::EmptyDurationScale;}
    R.ADS=FMath::Max(.001,R.ADS*(1+R.ADSPercent));
    R.Handling=FWeaponHandling::FromIndices(R.Recoil*R.RecoilMultiplier,R.Shake*R.ShakeMultiplier);
    R.Recoil=R.Handling.RecoilIndex;R.Shake=R.Handling.ShakeIndex;return R;
}
bool UGunsmithSystem::Begin(const FString& Id)
{
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();const auto* I=Profile->FindItem(Id);
    if(!I||I->Place>1||!Weapon(I->Definition))return false;
    InstanceId=Id;DefinitionId=I->Definition;Original=Installed(*I);Preview=Original;bOpen=true;Status=TEXT("选择配件预览，应用后保存");OnChanged.Broadcast();return true;
}
bool UGunsmithSystem::Select(const FString& Slot,const FString& Id)
{
    if(!bOpen||!Option(DefinitionId,Slot,Id))return false;
    if(Part(Preview,Slot)==Id)return true;
    if(Id==TEXT("false"))Preview.Remove(Slot);else Preview.Add(Slot,Id);
    Status=TEXT("预览已更新，应用后保存");OnChanged.Broadcast();return true;
}
int32 UGunsmithSystem::Pending()const{int32 Count=0;for(const auto& S:SlotKeys)if(Part(Original,S)!=Part(Preview,S))++Count;return Count;}
bool UGunsmithSystem::CanApply(FString& Reason)const
{
    if(!bOpen||!Pending()){Reason=TEXT("当前配置已应用");return false;}
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();const auto* I=P->FindItem(InstanceId);
    if(!I||I->Place>1||I->Definition!=DefinitionId){Reason=TEXT("枪械已不在背包或装备栏中");return false;}
    if(!Installed(*I).OrderIndependentCompareEqual(Original)){Reason=TEXT("枪械改装已发生变化，请重新选择");return false;}
    if(const auto* Pawn=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0)))if(I->Place==1&&I->Cell==P->Snapshot().ActiveWeaponSlot&&(Pawn->IsReloading()||Pawn->GetWeaponState()==EAKMWeaponState::Equipping)){Reason=TEXT("请等待换弹或装备动作结束");return false;}
    return true;
}
bool UGunsmithSystem::Apply()
{
    if(!CanApply(Status))return false;
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Profile->SyncRuntime();auto State=Profile->Snapshot();
    const int32 Index=State.Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==InstanceId;});if(Index<0)return false;
    auto& I=State.Items[Index];TSharedPtr<FJsonObject> Data;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data))return false;
    auto Parts=MakeShared<FJsonObject>();for(const auto& P:Preview){if(P.Value==TEXT("true"))Parts->SetBoolField(P.Key,true);else Parts->SetStringField(P.Key,P.Value);}
    Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Data->SetNumberField(TEXT("gunsmith_version"),1);I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&I.Data));
    const int32 Overflow=FMath::Max(0,I.Magazine-Calculate(DefinitionId,Preview).Capacity);
    if(Overflow){I.Magazine-=Overflow;const auto Ammo=Profile->CreateItem(Weapon(DefinitionId)->Ammo,Overflow);if(Ammo.Data.IsEmpty()||!ColdSteelInventory::Insert(State.Items,Ammo)){Status=TEXT("背包无空间收回弹药，改造未应用");return false;}}
    if(!Profile->CommitState(State)){Status=Profile->ResultMessage();return false;}
    Original=Preview;Status=TEXT("已应用改造并保存");OnChanged.Broadcast();return true;
}
void UGunsmithSystem::Undo(){Preview=Original;Status=TEXT("已撤销预览");OnChanged.Broadcast();}
void UGunsmithSystem::Close(){bOpen=false;Preview.Reset();Original.Reset();InstanceId.Reset();DefinitionId.Reset();}
