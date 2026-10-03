#include "GunsmithSystem.h"
#include "G18WeaponAssets.h"
#include "Staff/StaffCatalog.h"
#include "FrostSwordRunes.h"
#include "PistolDualWieldComponent.h"
#include "PistolGripSurface.h"
#include "M4DrumReloadTiming.h"
#include "M1911WeaponAssets.h"
#include "DanWesson715WeaponAssets.h"
#include "Animation/AnimSequence.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../Production/ProductionToolEnhance.h"
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
FGunsmithStats UGunsmithSystem::CalculateItem(const FColdSteelItem& Item,const FGunsmithParts& Parts) const
{
    auto S=Calculate(Item.Definition,Parts);
    const auto O=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Q=nullptr;
    if(!Weapon(Item.Definition)||!O||!O->TryGetObjectField(TEXT("_assemblyQuality"),Q)||!Q||!*Q)return S;
    const double Recoil=FMath::Clamp(Num(*Q,TEXT("recoil"),1),.88,1.);
    const double Spread=FMath::Clamp(Num(*Q,TEXT("spread"),1),.85,1.);
    S.Recoil*=Recoil;S.RecoilMultiplier*=Recoil;
    S.Handling.RecoilIndex=S.Recoil;S.Handling.RecoilScale*=Recoil;S.Spread*=Spread;
    return S;
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
        PistolGripSurface::MergeOptions(Catalog,O,W.Allowed);
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
        if(W.Id==TEXT("ue_m1911") || W.Id==G18WeaponAssets::Definition)
        {
            if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*(W.Id==G18WeaponAssets::Definition ? G18WeaponAssets::AnimationPath(TEXT("reload")) : M1911WeaponAssets::AnimationPath(TEXT("reload")))))W.Base.Reload=Clip->GetPlayLength();
            if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*(W.Id==G18WeaponAssets::Definition ? G18WeaponAssets::AnimationPath(TEXT("reload_empty")) : M1911WeaponAssets::AnimationPath(TEXT("reload_empty")))))W.Base.EmptyReload=Clip->GetPlayLength();
        }
        // 腰射散布系数：参考静止锥是 0.0175 rad/轴（GetHipSpread 的 ×2 括号内），
        // 本枪系数与配件 hip_spread_mult 连乘后驱动真实锥角与准星内缘；1 = 参考枪，0 = 无腰射散布。
        W.Base.Spread=Num(B,TEXT("spread_mult"),1);
        W.Base.Damage=Num(B,TEXT("damage"),25);W.Base.Speed=Num(B,TEXT("bullet_speed"),90);W.Base.Range=Num(B,TEXT("effective_range"),40);
        for(const auto& S:O->GetObjectField(TEXT("options"))->Values){TArray<FGunsmithOption> Options;
            for(const auto& Entry:S.Value->AsArray()){const auto P=Entry->AsObject();FGunsmithOption A;A.Id=P->GetStringField(TEXT("id"));A.Name=P->GetStringField(TEXT("name"));A.Description=P->GetStringField(TEXT("description"));
                for(const auto& E:P->GetArrayField(TEXT("effects")))A.Effects.Emplace(E->AsObject()->GetStringField(TEXT("text")),Num(E->AsObject(),TEXT("benefit")));
                const auto T=P->GetObjectField(TEXT("stats"));A.ADS=Num(T,TEXT("ads_percent"));A.Recoil=Num(T,TEXT("recoil_mult"),1);A.Shake=Num(T,TEXT("shake_mult"),1);A.Stability=Num(T,TEXT("stability_mult"),1);
                A.ADSSeconds=Num(T,TEXT("ads_seconds"));A.Speed=Num(T,TEXT("bullet_speed_mult"),1);A.Interval=Num(T,TEXT("fire_interval_mult"),1);A.Spread=Num(T,TEXT("hip_spread_mult"),1);A.Range=Num(T,TEXT("range_mult"),1);A.Reload=Num(T,TEXT("reload_mult"),1);A.EmptyReload=Num(T,TEXT("empty_reload_mult"),A.Reload);A.Magazine=Num(T,TEXT("mag_delta"));Options.Add(A);
            }W.Options.Add(FString(*S.Key),Options);
        }Weapons.Add(W.Id,W);
    }
    LoadMeleeCatalog();
    LoadToolCatalog();
    LoadBowCatalog();
    LoadStaffCatalog();
}
void UGunsmithSystem::Deinitialize(){Close();Super::Deinitialize();}
const FGunsmithWeapon* UGunsmithSystem::Weapon(const FString& D)const{return Weapons.Find(D);}
FString UGunsmithSystem::CategoryLabel(const FString& Definition,const FString& Slot) const
{
    if(Slot==TEXT("reargrip") && PistolGripSurface::Supports(Weapon(Definition)))return TEXT("握把防滑纹");
    const int32 Index=Slots(Definition).IndexOfByKey(Slot);
    const auto& Names=Categories(Definition);
    return Names.IsValidIndex(Index)?Names[Index]:TEXT("配件");
}
const FGunsmithOption* UGunsmithSystem::Option(const FString& D,const FString& S,const FString& Id)const{const auto* W=ModifiableWeapon(D);if(!W||!W->Allowed.Contains(S))return nullptr;const auto* A=W->Options.Find(S);return A?A->FindByPredicate([&](const auto& V){return V.Id==Id;}):nullptr;}
FGunsmithParts UGunsmithSystem::Normalize(const FString& D,const FGunsmithParts& Input)const
{
    FGunsmithParts Result;
    for(const auto& P:Input)
    {
        FString Slot=P.Key;
        // Earlier PKM instances stored the optional bipod in the grip slot.
        // Only an explicitly installed old bipod migrates; empty/new loadouts
        // stay empty, and an explicit new-slot choice always wins.
        if(D==TEXT("ue_pkm_lowpoly") && Slot==TEXT("underbarrel") && P.Value==TEXT("pkm_bipod"))
        {
            if(Input.Contains(TEXT("bipod")))continue;
            Slot=TEXT("bipod");
        }
        FString Id=Slot==TEXT("blade_2")?ColdSteelFrostRunes::Upgrade(D,P.Value):P.Value;
        if(Slot==TEXT("stock")&&Id==TEXT("true"))Id=TEXT("compact");
        if(Id!=TEXT("false")&&Option(D,Slot,Id))Result.Add(Slot,Id);
    }
    // Named factory parts are real options with stats. Resolve legacy empty /
    // false factory slots through the catalog, preserving every installed
    // replacement. Only weapons explicitly declaring defaults opt into this.
    const auto* W=ModifiableWeapon(D);
    const TSharedPtr<FJsonObject>* Factory=nullptr;
    if(W && W->Source && W->Source->TryGetObjectField(TEXT("default_parts"),Factory))
        for(const auto& P:(*Factory)->Values)
        {
            const FString Slot(*P.Key);
            FString Id;
            if(!Result.Contains(Slot) && P.Value->TryGetString(Id) && Option(D,Slot,Id))
                Result.Add(Slot,Id);
        }
    return Result;
}
FGunsmithParts UGunsmithSystem::Installed(const FColdSteelItem& I)const
{
    if(IsStaff(I.Definition))return Normalize(I.Definition,ColdSteelStaff::Installed(I));
    FGunsmithParts P;TSharedPtr<FJsonObject> O;const TSharedPtr<FJsonObject>* Parts=nullptr;
    if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),O)&&O->TryGetObjectField(TEXT("gunsmith_parts"),Parts))for(const auto& Pair:(*Parts)->Values){FString Value;if(Pair.Value->Type==EJson::Boolean)Value=Pair.Value->AsBool()?TEXT("true"):TEXT("false");else if(Pair.Value->Type==EJson::String)Value=Pair.Value->AsString();P.Add(FString(*Pair.Key),Value);}
    return Normalize(I.Definition,P);
}
FGunsmithStats UGunsmithSystem::Calculate(const FString& D,const FGunsmithParts& P)const
{
    const auto* W=ModifiableWeapon(D);if(!W)return {};auto R=W->Base;
    if(IsStaff(D)){R.ActiveParts=Normalize(D,P).Num();return R;}
    if(IsBow(D))
    {
        for(const auto& Pair:Normalize(D,P))
        {
            const auto& M=Option(D,Pair.Key,Pair.Value)->Bow;
            R.Bow.Damage*=M.Damage;R.Bow.Draw*=M.Draw;R.Bow.Speed*=M.Speed;R.Bow.Stamina*=M.Stamina;
            R.Bow.Nock*=M.Nock;R.Bow.Hold*=M.Hold;R.Bow.Sway*=M.Sway;R.Bow.Spread*=M.Spread;R.Bow.ADS*=M.ADS;
            ++R.ActiveParts;
        }
        R.Damage*=R.Bow.Damage;R.Interval*=R.Bow.Draw;R.Speed*=R.Bow.Speed;R.ADS*=R.Bow.ADS;
        return R;
    }
    if(IsMelee(D))
    {
        for(const auto& Pair:Normalize(D,P))
        {
            const auto& M=Option(D,Pair.Key,Pair.Value)->Melee;
            R.Melee.Damage*=M.Damage;R.Melee.AttackSpeed*=M.AttackSpeed;R.Melee.Range*=M.Range;
            R.Melee.Stamina*=M.Stamina;R.Melee.BlockStamina*=M.BlockStamina;R.Melee.HitReaction*=M.HitReaction;R.Melee.BlockReduction*=M.BlockReduction;
            R.Melee.KillStaminaMaxRatio=FMath::Clamp(R.Melee.KillStaminaMaxRatio+M.KillStaminaMaxRatio,0.,1.);
            R.Melee.ToughnessDamage*=M.ToughnessDamage;
            R.Melee.PhysicalArmorPenetration=FMath::Clamp(R.Melee.PhysicalArmorPenetration+M.PhysicalArmorPenetration,0.,1.);
            R.Melee.ComboSecond*=M.ComboSecond;R.Melee.ComboThird*=M.ComboThird;
            R.Melee.ComboThirdToughness*=M.ComboThirdToughness;
            R.Melee.MagicCooldown*=M.MagicCooldown;R.Melee.MagicDamage*=M.MagicDamage;
            R.Melee.MagicCost*=M.MagicCost;
            R.Melee.HeavyDamage*=M.HeavyDamage;R.Melee.Knockback*=M.Knockback;
            R.Melee.HeavyDamageAdd+=M.HeavyDamageAdd;
            R.Melee.HeavyToughness*=M.HeavyToughness;
            R.Melee.CooldownReduceSecondsPerHit+=M.CooldownReduceSecondsPerHit;
            R.Melee.QuickCombatDamageAdd+=M.QuickCombatDamageAdd;
            R.Melee.QuickCombatKnockback*=M.QuickCombatKnockback;
            R.Melee.QuickCombatToughness*=M.QuickCombatToughness;
            R.Melee.QuickCombatBleedChance=FMath::Max(R.Melee.QuickCombatBleedChance,M.QuickCombatBleedChance);
            R.Melee.bQuickCombatAOE|=M.bQuickCombatAOE;
            R.Melee.RuneIntelligence+=M.RuneIntelligence;R.Melee.RuneWisdom+=M.RuneWisdom;
            R.Melee.InnateErosionMultiplier*=M.InnateErosionMultiplier;
            R.Melee.RuneVulnerability=FMath::Max(R.Melee.RuneVulnerability,M.RuneVulnerability);
            R.Melee.RuneVulnerabilitySeconds=FMath::Max(R.Melee.RuneVulnerabilitySeconds,M.RuneVulnerabilitySeconds);
            R.Melee.ParryWindow*=M.ParryWindow;R.Melee.RiposteSpeed*=M.RiposteSpeed;R.Melee.RiposteStamina*=M.RiposteStamina;
            R.Melee.RiposteSeconds=FMath::Max(R.Melee.RiposteSeconds,M.RiposteSeconds);
            R.Melee.ClovenSeconds=FMath::Max(R.Melee.ClovenSeconds,M.ClovenSeconds);
            R.Melee.ClovenPhysical*=M.ClovenPhysical;R.Melee.ClovenToughness*=M.ClovenToughness;
            ++R.ActiveParts;
        }
        R.Damage*=R.Melee.Damage;R.Interval/=R.Melee.AttackSpeed;R.Range*=R.Melee.Range;
        return R;
    }
    if(IsTool(D))
    {
        // 采集工具：倍率相乘、绝对值相加；采集与自卫共用这一份结果，UI 不二次换算。
        for(const auto& Pair:Normalize(D,P))
        {
            const auto& T=Option(D,Pair.Key,Pair.Value)->Tool;
            R.Tool.Damage*=T.Damage;R.Tool.AttackSpeed*=T.AttackSpeed;R.Tool.Stamina*=T.Stamina;
            R.Tool.CombatReach*=T.CombatReach;R.Tool.ToughnessDamage*=T.ToughnessDamage;
            R.Tool.HarvestYield*=T.HarvestYield;R.Tool.HarvestReach*=T.HarvestReach;
            R.Tool.HarvestRadiusAddCM+=T.HarvestRadiusAddCM;
            R.Tool.BonusHarvestChance+=T.BonusHarvestChance;
            R.Tool.CriticalChanceAdd+=T.CriticalChanceAdd;
            R.Tool.HarvestHitsAdd+=T.HarvestHitsAdd;
            ++R.ActiveParts;
        }
        R.Tool.BonusHarvestChance=FMath::Clamp(R.Tool.BonusHarvestChance,0.,1.);
        R.Tool.CriticalChanceAdd=FMath::Max(0.,R.Tool.CriticalChanceAdd);
        R.Damage*=R.Tool.Damage;
        R.Interval/=FMath::Clamp(R.Tool.AttackSpeed,.25,4.);
        R.Range*=R.Tool.CombatReach;
        return R;
    }
    if(D==DanWesson715WeaponAssets::Definition&&Part(Normalize(D,P),DanWesson715WeaponAssets::ReloadDeviceSlot)==DanWesson715WeaponAssets::Speedloader)
    {R.Reload=DanWesson715WeaponAssets::EmptyReload;R.EmptyReload=DanWesson715WeaponAssets::EmptyReload;}
    for(const auto& Pair:Normalize(D,P)){const auto& A=*Option(D,Pair.Key,Pair.Value);R.ADSPercent+=A.ADS;R.ADSSeconds+=A.ADSSeconds;R.RecoilMultiplier*=A.Recoil;R.ShakeMultiplier*=A.Shake;R.StabilityMultiplier*=A.Stability;R.Capacity+=A.Magazine;R.Interval*=A.Interval;R.Reload*=A.Reload;R.EmptyReload*=A.EmptyReload;R.Speed*=A.Speed;R.Range*=A.Range;R.Spread*=A.Spread;++R.ActiveParts;}
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
    InstanceId=Id;DefinitionId=I->Definition;Original=Installed(*I);Preview=Original;bOpen=true;DraftEnhanceLevelValue=0;
    Status=TEXT("选择配件预览，应用后保存");OnChanged.Broadcast();return true;
}
bool UGunsmithSystem::Select(const FString& Slot,const FString& Id)
{
    if(!bOpen||!Option(DefinitionId,Slot,Id))return false;
    if(Part(Preview,Slot)==Id)return true;
    if(Id==TEXT("false"))Preview.Remove(Slot);else Preview.Add(Slot,Id);
    Status=TEXT("预览已更新，应用后保存");OnChanged.Broadcast();return true;
}
int32 UGunsmithSystem::CurrentEnhanceLevel()const
{
    if(!IsTool(DefinitionId))return 0;
    const auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();const auto* I=P?P->FindItem(InstanceId):nullptr;
    return I?ColdSteelToolEnhance::Level(*I):0;
}
bool UGunsmithSystem::CanEnhanceNow(int32& OutNextLevel)const
{
    OutNextLevel=0;
    const auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();const auto* I=P?P->FindItem(InstanceId):nullptr;
    if(!IsTool(DefinitionId)||!I)return false;
    return ColdSteelToolEnhance::CanEnhance(*I,OutNextLevel);
}
bool UGunsmithSystem::SetDraftEnhanceLevel(int32 Level)
{
    // 逐级 +1、不可降级、不可跳级：只有「当前等级+1」这一个值能被接受，其余一律拒绝并保持草稿不变。
    int32 Next=0;
    if(Level<=0||!CanEnhanceNow(Next)||Level!=Next)return false;
    if(DraftEnhanceLevelValue==Level)return true;
    DraftEnhanceLevelValue=Level;
    Status=TEXT("预览已更新，应用后保存");OnChanged.Broadcast();return true;
}
int32 UGunsmithSystem::Pending()const
{
    int32 Count=0;for(const auto& S:Slots(DefinitionId))if(Part(Original,S)!=Part(Preview,S))++Count;
    // 强化草稿与改造件分开计数：草稿只可能是「当前+1」这一个合法值，非 0 即一项待应用。
    if(DraftEnhanceLevelValue>0)++Count;
    return Count;
}
bool UGunsmithSystem::CanApply(FString& Reason)const
{
    if(!bOpen||!Pending()){Reason=TEXT("当前配置已应用");return false;}
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();const auto* I=P->FindItem(InstanceId);
    if(!I||I->Place>1||I->Definition!=DefinitionId){Reason=TEXT("武器已不在背包或装备栏中");return false;}
    if(!Installed(*I).OrderIndependentCompareEqual(Original)){Reason=TEXT("武器改装已发生变化，请重新选择");return false;}
    if(const auto* Pawn=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0)))
    {
        const bool ActiveOffhand=Pawn->HasOffhandPistol() && Pawn->DualPistols->Hand(1).Item.InstanceId==I->InstanceId;
        if(I->Place==1 && (I->Cell==P->Snapshot().ActiveWeaponSlot || ActiveOffhand)
            && (Pawn->IsReloading() || Pawn->GetWeaponState()==EAKMWeaponState::Equipping))
        {Reason=TEXT("请等待换弹或装备动作结束");return false;}
    }
    return true;
}
FString UGunsmithSystem::ApplyFeedback()const
{
    FString Reason;
    if(Pending()>0&&!CanApply(Reason))return Reason;
    return Status;
}
bool UGunsmithSystem::Apply()
{
    if(!CanApply(Status))return false;
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Profile->SyncRuntime();auto State=Profile->Snapshot();
    const int32 Index=State.Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==InstanceId;});if(Index<0)return false;
    auto& I=State.Items[Index];TSharedPtr<FJsonObject> Data;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data))return false;
    auto Parts=MakeShared<FJsonObject>();for(const auto& P:Preview){if(P.Value==TEXT("true"))Parts->SetBoolField(P.Key,true);else Parts->SetStringField(P.Key,P.Value);}
    Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Data->SetNumberField(TEXT("gunsmith_version"),1);
    // 强化等级与 gunsmith_parts 同一次提交：都写进这一份 State 的 Item.Data，随后走同一个 CommitState。
    // 缺省 1 级不写回（不批量迁移旧存档），也不放进 gunsmith_parts、不进定义刷新白名单。
    if(DraftEnhanceLevelValue>0)Data->SetNumberField(TEXT("tool_enhance_level"),DraftEnhanceLevelValue);
    I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&I.Data));
    const int32 Overflow=IsStaff(DefinitionId)||IsBow(DefinitionId)||IsMelee(DefinitionId)||IsTool(DefinitionId)?0:FMath::Max(0,I.Magazine-Calculate(DefinitionId,Preview).Capacity);
    if(Overflow){const int32 Virtual=FMath::Min(Overflow,I.VirtualMagazineAmmo);I.Magazine-=Overflow;I.VirtualMagazineAmmo-=Virtual;if(!Profile->AddAmmoToState(State,Profile->AmmoDefinitionFor(I),Overflow-Virtual)){Status=TEXT("弹药无法退回弹药袋，改造未应用");return false;}}
    // Staff customization follows the same free apply/save transaction as firearms.
    if(IsStaff(DefinitionId))I=ColdSteelStaff::Resolve(I);
    if(!Profile->CommitState(State)){Status=Profile->ResultMessage();return false;}
    Original=Preview;DraftEnhanceLevelValue=0;Status=TEXT("已应用改造并保存");OnChanged.Broadcast();return true;
}
void UGunsmithSystem::Undo(){Preview=Original;DraftEnhanceLevelValue=0;Status=TEXT("已撤销预览");OnChanged.Broadcast();}
void UGunsmithSystem::Close(){bOpen=false;Preview.Reset();Original.Reset();DraftEnhanceLevelValue=0;InstanceId.Reset();DefinitionId.Reset();}
