#include "GunsmithSystem.h"
#include "PistolDualWieldComponent.h"
#include "M4DrumReloadTiming.h"
#include "M1911WeaponAssets.h"
#include "DanWesson715WeaponAssets.h"
#include "Animation/AnimSequence.h"
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
        // Explicit opt-in only: firearms never stagger monsters unless the catalog
        // entry says so ("hit_stagger": true).
        O->TryGetBoolField(TEXT("hit_stagger"),W.bHitStagger);
        // Common numeric parts apply to every catalog weapon, including future entries.
        const TSharedPtr<FJsonObject>* Common=nullptr;
        if(Catalog->TryGetObjectField(TEXT("common_options"),Common))
        {
            auto Options=O->GetObjectField(TEXT("options"));
            for(const auto& Slot:(*Common)->Values)
            {
                W.Allowed.AddUnique(FString(*Slot.Key));
                TArray<TSharedPtr<FJsonValue>> Merged;
                const TArray<TSharedPtr<FJsonValue>>* Existing=nullptr;
                if(Options->TryGetArrayField(Slot.Key,Existing))Merged=*Existing;
                for(const auto& Entry:Slot.Value->AsArray())
                {
                    const FString Id=Entry->AsObject()->GetStringField(TEXT("id"));
                    if(!Merged.ContainsByPredicate([&](const auto& V){return V->AsObject()->GetStringField(TEXT("id"))==Id;}))Merged.Add(Entry);
                }
                Options->SetArrayField(Slot.Key,Merged);
            }
        }
        const auto B=O->GetObjectField(TEXT("base"));W.Ammo=B->GetStringField(TEXT("ammo_item_id"));
        W.Base.ADS=FMath::Loge(20.)/Num(B,TEXT("ads_smooth"),9.98577424518);W.Base.Capacity=Num(B,TEXT("mag_size"),30);
        W.Base.Recoil=Num(B,TEXT("recoil"),100);W.Base.Shake=Num(B,TEXT("camera_shake"),100);W.Base.Interval=Num(B,TEXT("fire_interval"),.13);
        W.Base.StabilityMultiplier=Num(B,TEXT("stability_mult"),1);
        W.Base.BurstCount=FMath::Max(1,int32(Num(B,TEXT("burst_count"),1)));
        W.Base.BurstDelay=FMath::Max(0.,Num(B,TEXT("burst_delay")));
        W.Base.Reload=Num(B,TEXT("reload_time"),1.5);W.Base.EmptyReload=Num(B,TEXT("empty_reload_time"));if(W.Base.EmptyReload<=0)W.Base.EmptyReload=W.Base.Reload;
        // M1911 uses its imported action lengths as the base for both stats and
        // playback. Attachment reload multipliers still scale the whole action.
        if(W.Id==DanWesson715WeaponAssets::Definition)
        {
            W.Base.Reload=DanWesson715WeaponAssets::SingleDuration(5);
            W.Base.EmptyReload=DanWesson715WeaponAssets::SingleDuration(6, true);
            if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*DanWesson715WeaponAssets::SingleAnimationPath(1,5)))W.Base.Reload=Clip->GetPlayLength();
            if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*DanWesson715WeaponAssets::SingleAnimationPath(0,6)))W.Base.EmptyReload=Clip->GetPlayLength();
        }
        if(W.Id==TEXT("ue_m1911"))
        {
            if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*M1911WeaponAssets::AnimationPath(TEXT("reload"))))W.Base.Reload=Clip->GetPlayLength();
            if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*M1911WeaponAssets::AnimationPath(TEXT("reload_empty"))))W.Base.EmptyReload=Clip->GetPlayLength();
        }
        W.Base.Damage=Num(B,TEXT("damage"),25);W.Base.Speed=Num(B,TEXT("bullet_speed"),90);W.Base.Range=Num(B,TEXT("effective_range"),40);
        for(const auto& S:O->GetObjectField(TEXT("options"))->Values){TArray<FGunsmithOption> Options;
            for(const auto& Entry:S.Value->AsArray()){const auto P=Entry->AsObject();FGunsmithOption A;A.Id=P->GetStringField(TEXT("id"));A.Name=P->GetStringField(TEXT("name"));A.Description=P->GetStringField(TEXT("description"));
                for(const auto& E:P->GetArrayField(TEXT("effects")))A.Effects.Emplace(E->AsObject()->GetStringField(TEXT("text")),Num(E->AsObject(),TEXT("benefit")));
                const auto T=P->GetObjectField(TEXT("stats"));A.ADS=Num(T,TEXT("ads_percent"));A.Recoil=Num(T,TEXT("recoil_mult"),1);A.Shake=Num(T,TEXT("shake_mult"),1);A.Stability=Num(T,TEXT("stability_mult"),1);
                A.ADSSeconds=Num(T,TEXT("ads_seconds"));A.Speed=Num(T,TEXT("bullet_speed_mult"),1);A.Interval=Num(T,TEXT("fire_interval_mult"),1);A.Spread=Num(T,TEXT("hip_spread_mult"),1);A.Range=Num(T,TEXT("range_mult"),1);A.Reload=Num(T,TEXT("reload_mult"),1);A.Magazine=Num(T,TEXT("mag_delta"));Options.Add(A);
            }W.Options.Add(FString(*S.Key),Options);
        }Weapons.Add(W.Id,W);
    }
    LoadMeleeCatalog();
}
void UGunsmithSystem::Deinitialize(){Close();Super::Deinitialize();}
const FGunsmithWeapon* UGunsmithSystem::Weapon(const FString& D)const{return Weapons.Find(D);}
const FGunsmithOption* UGunsmithSystem::Option(const FString& D,const FString& S,const FString& Id)const{const auto* W=ModifiableWeapon(D);if(!W||!W->Allowed.Contains(S))return nullptr;const auto* A=W->Options.Find(S);return A?A->FindByPredicate([&](const auto& V){return V.Id==Id;}):nullptr;}
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
    const auto* W=ModifiableWeapon(D);if(!W)return {};auto R=W->Base;
    if(IsMelee(D))
    {
        for(const auto& Pair:Normalize(D,P))
        {
            const auto& M=Option(D,Pair.Key,Pair.Value)->Melee;
            R.Melee.Damage*=M.Damage;R.Melee.AttackSpeed*=M.AttackSpeed;R.Melee.Range*=M.Range;
            R.Melee.Stamina*=M.Stamina;R.Melee.HitReaction*=M.HitReaction;R.Melee.BlockReduction*=M.BlockReduction;
            R.Melee.ComboSecond*=M.ComboSecond;R.Melee.ComboThird*=M.ComboThird;
            R.Melee.MagicCooldown*=M.MagicCooldown;R.Melee.MagicDamage*=M.MagicDamage;
            R.Melee.MagicCost*=M.MagicCost;
            R.Melee.HeavyDamage*=M.HeavyDamage;R.Melee.Knockback*=M.Knockback;
            R.Melee.HeavyDamageAdd+=M.HeavyDamageAdd;
            R.Melee.QuickCombatDamageAdd+=M.QuickCombatDamageAdd;
            R.Melee.QuickCombatKnockback*=M.QuickCombatKnockback;
            R.Melee.RuneIntelligence+=M.RuneIntelligence;R.Melee.RuneWisdom+=M.RuneWisdom;
            R.Melee.RuneVulnerability=FMath::Max(R.Melee.RuneVulnerability,M.RuneVulnerability);
            R.Melee.RuneVulnerabilitySeconds=FMath::Max(R.Melee.RuneVulnerabilitySeconds,M.RuneVulnerabilitySeconds);
            R.Melee.ParryWindow*=M.ParryWindow;R.Melee.RiposteSpeed*=M.RiposteSpeed;R.Melee.RiposteStamina*=M.RiposteStamina;
            R.Melee.RiposteSeconds=FMath::Max(R.Melee.RiposteSeconds,M.RiposteSeconds);
            ++R.ActiveParts;
        }
        R.Damage*=R.Melee.Damage;R.Interval/=R.Melee.AttackSpeed;R.Range*=R.Melee.Range;
        return R;
    }
    if(D==DanWesson715WeaponAssets::Definition&&Part(Normalize(D,P),DanWesson715WeaponAssets::ReloadDeviceSlot)==DanWesson715WeaponAssets::Speedloader)
    {R.Reload=DanWesson715WeaponAssets::EmptyReload;R.EmptyReload=DanWesson715WeaponAssets::EmptyReload;}
    for(const auto& Pair:Normalize(D,P)){const auto& A=*Option(D,Pair.Key,Pair.Value);R.ADSPercent+=A.ADS;R.ADSSeconds+=A.ADSSeconds;R.RecoilMultiplier*=A.Recoil;R.ShakeMultiplier*=A.Shake;R.StabilityMultiplier*=A.Stability;R.Capacity+=A.Magazine;R.Interval*=A.Interval;R.Reload*=A.Reload;R.EmptyReload*=A.Reload;R.Speed*=A.Speed;R.Range*=A.Range;R.Spread*=A.Spread;++R.ActiveParts;}
    if(D==TEXT("ue_m4a1")&&Part(Normalize(D,P),TEXT("magazine"))==TEXT("large_drum"))
    {R.Reload*=M4DrumReloadTiming::NormalDurationScale;R.EmptyReload*=M4DrumReloadTiming::EmptyDurationScale;}
    R.BurstDelay*=R.Interval/FMath::Max(.001,W->Base.Interval);
    R.ADS=FMath::Max(.001,R.ADS*(1+R.ADSPercent)+R.ADSSeconds);
    R.Handling=FWeaponHandling::FromIndices(R.Recoil*R.RecoilMultiplier,R.Shake*R.ShakeMultiplier,R.StabilityMultiplier);
    R.Recoil=R.Handling.RecoilIndex;R.Shake=R.Handling.ShakeIndex;return R;
}
bool UGunsmithSystem::Begin(const FString& Id)
{
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();const auto* I=Profile->FindItem(Id);
    if(!I||I->Place>1||!ModifiableWeapon(I->Definition))return false;
    InstanceId=Id;DefinitionId=I->Definition;Original=Installed(*I);Preview=Original;bOpen=true;
    Status=TEXT("选择配件预览，应用后保存");OnChanged.Broadcast();return true;
}
bool UGunsmithSystem::Select(const FString& Slot,const FString& Id)
{
    if(!bOpen||!Option(DefinitionId,Slot,Id))return false;
    if(Part(Preview,Slot)==Id)return true;
    if(Id==TEXT("false"))Preview.Remove(Slot);else Preview.Add(Slot,Id);
    Status=TEXT("预览已更新，应用后保存");OnChanged.Broadcast();return true;
}
int32 UGunsmithSystem::Pending()const{int32 Count=0;for(const auto& S:Slots(DefinitionId))if(Part(Original,S)!=Part(Preview,S))++Count;return Count;}
bool UGunsmithSystem::CanApply(FString& Reason)const
{
    if(!bOpen||!Pending()){Reason=TEXT("当前配置已应用");return false;}
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();const auto* I=P->FindItem(InstanceId);
    if(!I||I->Place>1||I->Definition!=DefinitionId){Reason=TEXT("武器已不在背包或装备栏中");return false;}
    if(!Installed(*I).OrderIndependentCompareEqual(Original)){Reason=TEXT("武器改装已发生变化，请重新选择");return false;}
    if(const auto* Pawn=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0)))
    {
        const bool ActiveOffhand=Pawn->IsDualWieldingPistols() && Pawn->DualPistols->Hand(1).Item.InstanceId==I->InstanceId;
        if(I->Place==1 && (I->Cell==P->Snapshot().ActiveWeaponSlot || ActiveOffhand)
            && (Pawn->IsReloading() || Pawn->GetWeaponState()==EAKMWeaponState::Equipping))
        {Reason=TEXT("请等待换弹或装备动作结束");return false;}
    }
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
    const int32 Overflow=IsMelee(DefinitionId)?0:FMath::Max(0,I.Magazine-Calculate(DefinitionId,Preview).Capacity);
    if(Overflow){const int32 Virtual=FMath::Min(Overflow,I.VirtualMagazineAmmo);I.Magazine-=Overflow;I.VirtualMagazineAmmo-=Virtual;if(!Profile->AddAmmoToState(State,Profile->AmmoDefinitionFor(I),Overflow-Virtual)){Status=TEXT("弹药无法退回弹药袋，改造未应用");return false;}}
    if(!Profile->CommitState(State)){Status=Profile->ResultMessage();return false;}
    Original=Preview;Status=TEXT("已应用改造并保存");OnChanged.Broadcast();return true;
}
void UGunsmithSystem::Undo(){Preview=Original;Status=TEXT("已撤销预览");OnChanged.Broadcast();}
void UGunsmithSystem::Close(){bOpen=false;Preview.Reset();Original.Reset();InstanceId.Reset();DefinitionId.Reset();}
