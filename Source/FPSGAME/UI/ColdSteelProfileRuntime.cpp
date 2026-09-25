#include "../Dungeon/DungeonLayout.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/WeaponReloadStages.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/RuneOrbBladesComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "ColdSteelPickup.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCoreStats.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "EngineUtils.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/FrostSwordRunes.h"
#include "Misc/SecureHash.h"

// 定时自动存档周期（秒）。战斗与修行增量先落在内存档案里（StageTraining），由这个时钟统一写盘：
// 旧口径是「待写盘时每 1 秒补一次」加「无条件每 5 秒一次」，战斗中几乎每秒都在写约 100 KB 的存档、
// 回读校验、再反序列化校验一遍，全部在游戏线程上。物品、装备、强化、仓库、弹药换装这类玩家主动
// 事务以及升级、退出仍然立即写盘，最多只会丢一个周期的战斗收益。0 表示关闭定时存档。
static TAutoConsoleVariable<float> SaveAutosaveSeconds(TEXT("fps.Save.AutosaveSeconds"),300.f,
    TEXT("Seconds between periodic checked autosaves. Combat and training progress is applied to the live profile immediately and lands on this clock. Inventory, equipment, enhancement, warehouse and ammo-switch transactions, level-ups and exit still save immediately. 0 disables the periodic save."),
    ECVF_Default);

using namespace ColdSteelInventory;
namespace
{
void StoreRevolverCaseCount(FColdSteelItem& Item, int32 Count)
{
    TSharedPtr<FJsonObject> Data;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data), Data) || !Data) return;
    Data->SetNumberField(TEXT("revolver_case_count"), Count);
    Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
}
bool IsRetiredWeapon(const FString& Id)
{
    static const TSet<FString> Retired = {TEXT("fps_akm"),TEXT("fps_hk416"),TEXT("fps_m16"),TEXT("fps_akm_classic"),TEXT("fps_qbz191"),TEXT("fps_p9"),TEXT("ue_pkm"),TEXT("ue_pkm_a"),TEXT("ammo_762x54r")};
    return Retired.Contains(Id);
}
bool RemoveRetiredWeapons(FColdSteelProfile& P)
{
    TSet<FString> Removed;
    for (const auto& I : P.Items) if (IsRetiredWeapon(I.Definition)) Removed.Add(I.InstanceId);
    bool Changed = P.Items.RemoveAll([](const auto& I){ return IsRetiredWeapon(I.Definition); }) > 0;
    Changed |= P.ArmoryReceived.RemoveAll([](const FString& Id){ return IsRetiredWeapon(Id); }) > 0;
    for (int32 N=0; N<P.Hotbar.Num(); ++N) {
        if (Removed.Contains(P.Hotbar[N]) || (P.HotbarDefinitions.IsValidIndex(N) && IsRetiredWeapon(P.HotbarDefinitions[N]))) {
            P.Hotbar[N].Reset(); if (P.HotbarDefinitions.IsValidIndex(N)) P.HotbarDefinitions[N].Reset(); Changed=true;
        }
    }
    // Clear the selected PKM family from saved quick bindings and its ammo pouch.
    for (auto& Binding : P.QuickBindings) {
        if (Removed.Contains(Binding.ItemId) || IsRetiredWeapon(Binding.ItemDefinition)) {
            Binding = FColdSteelQuickBinding(); Changed = true;
        }
    }
    Changed |= P.AmmoPouch.Remove(TEXT("ammo_762x54r")) > 0;
    if (Owner(P.Items,1,P.ActiveWeaponSlot)<0) {
        const int32 Other=P.ActiveWeaponSlot==6?9:6;
        if (Owner(P.Items,1,Other)>=0) { P.ActiveWeaponSlot=Other; Changed=true; }
    }
    return Changed;
}
FString ChecksumPath(const FString& Slot){return FPaths::ProjectSavedDir()/TEXT("SaveGames")/(Slot+TEXT(".sha1"));}
FString HashBytes(const TArray<uint8>& Data){uint8 Hash[20];FSHA1::HashBuffer(Data.GetData(),Data.Num(),Hash);return BytesToHex(Hash,20);}
UColdSteelProfileSave* ReadCheckedProfile(const FString& Slot)
{
    TArray<uint8> Bytes;FString Hash;
    if(!UGameplayStatics::LoadDataFromSlot(Bytes,Slot,0)||Bytes.Num()<32||Bytes.Num()>32*1024*1024||!FFileHelper::LoadFileToString(Hash,*ChecksumPath(Slot))||Hash!=HashBytes(Bytes))return nullptr;
    return Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromMemory(Bytes));
}
}
void UColdSteelStatusModel::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    RifleSkill=ColdSteelSkills::LoadDefinition();
    PistolSkill=ColdSteelSkills::LoadDefinition(TEXT("pistolMastery"));
    CriticalStrikeSkill=ColdSteelSkills::LoadDefinition(TEXT("criticalStrike"));
    FireballSkill=ColdSteelSkills::LoadDefinition(TEXT("fireball"));
    IceSpikeSkill=ColdSteelSkills::LoadDefinition(TEXT("iceSpike"));
    LightningSkill=ColdSteelSkills::LoadDefinition(TEXT("lightningStrike"));
    HolyLightSkill=ColdSteelSkills::LoadDefinition(TEXT("holyLight"));
    MeteorSkill=ColdSteelSkills::LoadDefinition(TEXT("meteor"));
    FlameArmorSkill=ColdSteelSkills::LoadDefinition(TEXT("flameArmor"));
    DodgeSkill=ColdSteelSkills::LoadDefinition(TEXT("dodge"));LoadStaminaTuning();
    DexterousHandsSkill=ColdSteelSkills::LoadDefinition(TEXT("dexterousHands"));
    QuickCombatSkill=ColdSteelSkills::LoadDefinition(TEXT("quickCombat"));
    RuneBladesSkill=ColdSteelSkills::LoadDefinition(TEXT("runeBlades"));
    ColdSteelSkills::Migrate(Current);
    FString Json; TSharedPtr<FJsonObject> Root;
    if(FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root))
        for(const auto& Pair:Root->Values){FString Data;FJsonSerializer::Serialize(Pair.Value->AsObject().ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Data));Definitions.Add(FString(*Pair.Key),Data);}
    LoadProductionDefinitions();LoadBowDefinitions();LoadAmmoCatalog();
    SaveSlot=TEXT("ColdSteelPlayer"); FString Requested;
    bAudit=FString(FCommandLine::Get()).Contains(TEXT("Audit"));
    if(FParse::Value(FCommandLine::Get(),TEXT("ColdSteelProfile="),Requested)) {
        if(!Requested.IsEmpty()&&Requested.Len()<64&&!Requested.Contains(TEXT("/"))&&!Requested.Contains(TEXT("\\"))&&!Requested.Contains(TEXT("..")))SaveSlot=TEXT("ColdSteel_")+Requested;
        else bPersistenceBlocked=true;
    } else if(bAudit)SaveSlot=TEXT("ColdSteel_AuditSession");
    for(FName Key:{FName("str"),FName("dex"),FName("intt"),FName("con"),FName("wis"),FName("luck")})Current.Attributes.Add(Key,10);
    Current.Hotbar.SetNum(4);Current.HotbarDefinitions.SetNum(4);Current.WarehouseLayoutVersion=1;NormalizeStamina(Current);Publish(Current);
    const bool Exists=UGameplayStatics::DoesSaveGameExist(SaveSlot+TEXT("_A"),0)||UGameplayStatics::DoesSaveGameExist(SaveSlot+TEXT("_B"),0);
    if(Exists){if(ReloadProfile()){GrantStartingArmory();if(!bAudit)GrantEnhancementMaterials();}return;}
    auto Seed=Snapshot();auto Weapon=CreateItem(TEXT("ue_m4a1"));Weapon.Place=1;Weapon.Cell=6;Seed.Items.Add(Weapon);
    for(const auto& Pair:TArray<TPair<FString,int64>>{{TEXT("hp_potion"),5},{TEXT("mp_potion"),3},{TEXT("gold"),200},{TEXT("ammo_556"),90},{TEXT("ammo_762"),90},{TEXT("ammo_127"),60}}) {
        if(AmmoType(Pair.Key)){AddAmmoToState(Seed,Pair.Key,Pair.Value);continue;}
        auto I=CreateItem(Pair.Key,Pair.Value); if(!I.Data.IsEmpty())Insert(Seed.Items,I);
    }
    for(int32 Index=0;Index<2;++Index){const FString Def=Index==0?TEXT("hp_potion"):TEXT("mp_potion");for(const auto& I:Seed.Items)if(I.Definition==Def){Seed.Hotbar[Index]=I.InstanceId;Seed.HotbarDefinitions[Index]=Def;break;}}
    if(CommitState(Seed)){GrantStartingArmory();if(!bAudit)GrantEnhancementMaterials();}
}
void UColdSteelStatusModel::Deinitialize(){SaveNow();Super::Deinitialize();}
FColdSteelProfile UColdSteelStatusModel::Snapshot() const {auto P=Current;P.Name=CharacterName;P.Class=CharacterClass;P.Level=Level;P.Points=AttributePoints;P.Attributes=Attributes;return P;}
void UColdSteelStatusModel::Publish(const FColdSteelProfile& P){Current=P;CharacterName=P.Name;CharacterClass=P.Class;Level=P.Level;AttributePoints=P.Points;Attributes=P.Attributes;bTrainingDirty=false;TrainingFlushAccumulator=0.f;OnStaminaChanged.Broadcast();}
bool UColdSteelStatusModel::CommitState(FColdSteelProfile State)
{
    return PersistState(MoveTemp(State),true);
}
bool UColdSteelStatusModel::PersistState(FColdSteelProfile State,bool bApplyPawn)
{
    if(bPersistenceBlocked||(GetWorld()&&GetWorld()->GetNetMode()!=NM_Standalone)){Message=TEXT("当前玩家数据不可写入");return false;}
    RemoveRetiredWeapons(State);
    bool AmmoChanged=false;
    if(!NormalizeAmmo(State,AmmoChanged)){Message=TEXT("弹药数据迁移失败，原存档保留");return false;}
    NormalizeProductionState(State);
    // Equipment has the highest action priority. Only a successfully published
    // equipment change interrupts the outgoing action in ApplyColdSteelProfile.
    ColdSteelSkills::Migrate(State);
    ColdSteelQuickBar::Migrate(State);
    ColdSteelQuickBar::MirrorLegacy(State);
    NormalizeStamina(State);
    // Original updateMaxStats preserves the missing HP/MP amount when maxima grow.
    if(State.Health>0)State.Health=FMath::Clamp(double(State.Health)+ResourceMaximum(State,false)-ResourceMaximum(Current,false),0.,ResourceMaximum(State,false));
    State.Mana=FMath::Clamp(double(State.Mana)+ResourceMaximum(State,true)-ResourceMaximum(Current,true),0.,ResourceMaximum(State,true));
    if(!ColdSteelWarehouse::MigrateLayout(State)){Message=TEXT("仓库布局迁移失败，原存档保留");return false;}
    FString Reason;if(!Validate(State,Reason)){Message=Reason;return false;}
    if(bAudit&&AuditFailNextSave){AuditFailNextSave=false;Message=TEXT("验收注入：保存失败，操作未提交");return false;}
    State.Version=2;
    State.Generation=Current.Generation+1;
    auto* Save=Cast<UColdSteelProfileSave>(UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));Save->Profile=State;
    const FString Slot=SaveSlot+(State.Generation%2?TEXT("_A"):TEXT("_B"));
    if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0)){Message=TEXT("保存失败，操作未提交");return false;}
    TArray<uint8> Written;
    if(!UGameplayStatics::LoadDataFromSlot(Written,Slot,0)||!FFileHelper::SaveStringToFile(HashBytes(Written),*ChecksumPath(Slot))){Message=TEXT("完整性记录写入失败，操作未提交");return false;}
    auto* Verify=ReadCheckedProfile(Slot);
    if(!Verify||Verify->Profile.Generation!=State.Generation||!Validate(Verify->Profile,Reason)){Message=TEXT("存档写入校验失败，操作未提交");return false;}
    QueueProgressNotices(Current,State);
    Publish(State);Message=TEXT("已保存");
    if(bApplyPawn)ApplyToPawn();
    OnChanged.Broadcast();return true;
}
// Automatic fire lands ten or more accepted hits per second, and every
// critical hit used to run the full checked transaction inside the damage call:
// two slot writes, two reads, a checksum write, two validations and a complete
// profile re-apply. That synchronous disk work on the game thread is what reads
// as stutter while shooting a monster. Training is now applied to the live
// profile immediately - so damage, rewards and panel readings stay exact - and
// the checked save is coalesced to the autosave clock.
//
// Deliberate trade-off (2026-09-18 audit, extended 2026-09-21): a hard crash can
// lose at most one autosave period of combat progress (fps.Save.AutosaveSeconds,
// default 300 s), and a rejected level-up save keeps the new level in memory until
// the next autosave self-heals it. Do not "fix" this back to a per-hit checked
// transaction - that is the stutter this staging removed.
bool UColdSteelStatusModel::StageTraining(FColdSteelProfile&& State)
{
    bool bLeveled=false;
    for(const auto& Pair:State.Skills)
    {
        const auto* Before=Current.Skills.Find(Pair.Key);
        if(!Before||Pair.Value.Level>Before->Level){bLeveled=true;break;}
    }
    bLeveled|=State.Level>Current.Level;
    Current=MoveTemp(State);
    // A level-up owns a progress notice plus derived stat changes, so it keeps
    // the immediate checked transaction. Ordinary hit experience does not.
    if(bLeveled)
    {
        if(PersistState(Snapshot(),true))return true;
        // A rejected save keeps the staged training queued for the next autosave.
        bTrainingDirty=true;TrainingFlushAccumulator=0.f;return false;
    }
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    // Coalesced panel refresh: readings already come from the live profile, so
    // the sheet does not need to rebuild once per bullet.
    const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0.;
    if(Now-LastTrainingPublish>=.15){LastTrainingPublish=Now;OnChanged.Broadcast();}
    return true;
}
bool UColdSteelStatusModel::ReloadProfile()
{
    UColdSteelProfileSave* Best=nullptr;FString Reason;bool BestFootprintMigrated=false;
    for(const TCHAR* S:{TEXT("_A"),TEXT("_B")})
    {
        auto* Save=ReadCheckedProfile(SaveSlot+S);if(!Save)continue;
        bool FootprintMigrated=false;
        // Wood changed from 1x1 to 1x2 on 2026-09-24. The old loader
        // rejected both slots before reaching its later wood migration.
        if(!MigrateLegacyWoodFootprints(Save->Profile,FootprintMigrated,Reason))
        {UE_LOG(LogTemp,Warning,TEXT("ColdSteel profile %s%s rejected: %s"),*SaveSlot,S,*Reason);continue;}
        if(!Best||Save->Profile.Generation>Best->Profile.Generation)
        {Best=Save;BestFootprintMigrated=FootprintMigrated;}
    }
    if(!Best){bPersistenceBlocked=true;Message=TEXT("两个存档版本均不可读取，已保留原文件");return false;}
    auto Clean=Best->Profile;
    int64 RecoveredGroundAmmo=0;
    for(const auto& Item:Clean.Items)if(Item.Place==2&&AmmoType(Item.Definition))RecoveredGroundAmmo+=Item.Count;
    bool AmmoMigrated=false;
    if(!NormalizeAmmo(Clean,AmmoMigrated)){bPersistenceBlocked=true;Message=TEXT("弹药迁移失败，原存档保留");return false;}
    const bool Migrated=Clean.WarehouseLayoutVersion==0;
    if(!ColdSteelWarehouse::MigrateLayout(Clean)){bPersistenceBlocked=true;Message=TEXT("仓库布局迁移失败，原存档保留");return false;}
    const bool SkillsMigrated=ColdSteelSkills::Migrate(Clean);
    const bool QuickBarMigrated=ColdSteelQuickBar::Migrate(Clean);
    const bool StaminaMigrated=NormalizeStamina(Clean);
    const bool AbandonedFireball=Clean.bFireballReserved;Clean.bFireballReserved=false;
    const bool AbandonedIce=Clean.bIceSpikeReserved;Clean.bIceSpikeReserved=false;
    const bool AbandonedQuick=Clean.bQuickCombatReserved;Clean.bQuickCombatReserved=false;
    bool Removed=RemoveRetiredWeapons(Clean)||Migrated||SkillsMigrated||QuickBarMigrated||StaminaMigrated||AbandonedFireball||AbandonedIce||AbandonedQuick||AmmoMigrated||BestFootprintMigrated;
    // Refresh authorized material rarity and scroll presentation on existing instances.
    for(auto& I:Clean.Items)
    {
        if(I.Definition==TEXT("wood"))
        {
            const FIntPoint Size=ColdSteelInventory::Footprint(I);
            if(I.Width!=Size.X||I.Height!=Size.Y){I.Width=Size.X;I.Height=Size.Y;Removed=true;}
            const FString* Catalog=Definitions.Find(I.Definition);
            TSharedPtr<FJsonObject> Data,Defaults;
            if(Catalog&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data)&&Data&&
                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Catalog),Defaults)&&Defaults)
            {
                FString Icon,Old;Defaults->TryGetStringField(TEXT("ue_icon"),Icon);Data->TryGetStringField(TEXT("ue_icon"),Old);
                if(!Icon.IsEmpty()&&Icon!=Old){Data->SetStringField(TEXT("ue_icon"),Icon);I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Removed=true;}
            }
        }
        if(I.Definition==ColdSteelFrostRunes::Definition)
        {
            const FString* Definition=Definitions.Find(I.Definition);
            TSharedPtr<FJsonObject> Data,Defaults;
            if(Definition&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data)&&Data&&
                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Definition),Defaults)&&Defaults)
            {
                bool Updated=false;
                for(const TCHAR* Key:{TEXT("innate_erosion_intelligence"),TEXT("innate_erosion_wisdom")})
                {
                    double Value=0,Old=0;
                    if(Defaults->TryGetNumberField(Key,Value)&&(!Data->TryGetNumberField(Key,Old)||Old!=Value))
                    {Data->SetNumberField(Key,Value);Updated=true;}
                }
                FString Description,OldDescription;Data->TryGetStringField(TEXT("desc"),OldDescription);
                if(Defaults->TryGetStringField(TEXT("desc"),Description)&&Description!=OldDescription)
                {Data->SetStringField(TEXT("desc"),Description);Updated=true;}
                if(Updated){I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Removed=true;}
            }
        }
        // Remove legacy gold selections outside the rune sword, and retain the
        // frost erosion-to-spirit migration through the existing A/B save commit.
        if(I.Definition!=TEXT("ue_rune_sword"))
        {
            TSharedPtr<FJsonObject> Data;const TSharedPtr<FJsonObject>* Parts=nullptr;FString Rune;
            if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data)&&Data&&
                Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&(*Parts)->TryGetStringField(TEXT("blade_2"),Rune))
            {
                const FString Replacement=ColdSteelFrostRunes::Upgrade(I.Definition,Rune);
                if(Replacement!=Rune)
                {
                    if(Replacement.IsEmpty())(*Parts)->RemoveField(TEXT("blade_2"));
                    else (*Parts)->SetStringField(TEXT("blade_2"),Replacement);
                    I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Removed=true;
                }
            }
        }
        // 武器归类以目录为准：PKM 从步枪改判机枪后，旧存档实例仍带着
        // weaponType:"rifle"，会让持械移速与专精结算继续走步枪分支。
        // 只同步目录里真实存在的 weaponType，且只在不同才写回。
        if(const FString* CatalogDefinition=Definitions.Find(I.Definition))
        {
            TSharedPtr<FJsonObject> CatalogData,ItemData;
            FString CatalogType,StoredType;
            if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*CatalogDefinition),CatalogData)&&CatalogData&&
                CatalogData->TryGetStringField(TEXT("weaponType"),CatalogType)&&!CatalogType.IsEmpty()&&
                FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),ItemData)&&ItemData&&
                ItemData->TryGetStringField(TEXT("weaponType"),StoredType)&&StoredType!=CatalogType)
            {
                ItemData->SetStringField(TEXT("weaponType"),CatalogType);
                I.Data.Reset();FJsonSerializer::Serialize(ItemData.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Removed=true;
            }
            // 条目说明同样以目录为准。物品实例存的是创建当时的目录快照，
            // 所以只改 items.json 时，已经持有的武器仍显示旧介绍
            // （实测：旧文案在 ColdSteelPlayer_A.sav 里各命中 1-2 处，新文案 0 处）。
            // 只同步纯展示文本，不碰数值、改造件或附魔数据。
            // 实例里没有该字段时也要补上：否则战斗目录的补全逻辑会继续留着旧值。
            FString CatalogDesc;
            if(CatalogData->TryGetStringField(TEXT("desc"),CatalogDesc)&&!CatalogDesc.IsEmpty())
            {
                FString StoredDesc;
                const bool bHasStored=FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),ItemData)
                    &&ItemData&&ItemData->TryGetStringField(TEXT("desc"),StoredDesc);
                if(!bHasStored||StoredDesc!=CatalogDesc)
                {
                    if(!ItemData)ItemData=MakeShared<FJsonObject>();
                    ItemData->SetStringField(TEXT("desc"),CatalogDesc);
                    I.Data.Reset();FJsonSerializer::Serialize(ItemData.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Removed=true;
                }
            }
        }
        const bool Material=I.Definition==TEXT("enhancement_stone")||I.Definition==TEXT("magic_dust");
        if(!Material&&I.Definition!=TEXT("enchant_scroll_heavy")&&I.Definition!=TEXT("enchant_scroll_sharp")&&I.Definition!=TEXT("enchant_scroll_skeleton")&&I.Definition!=TEXT("enchant_scroll_tarantula"))continue;
        const FString* Definition=Definitions.Find(I.Definition);if(!Definition)continue;
        TSharedPtr<FJsonObject> CurrentData,DefinitionData;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),CurrentData)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Definition),DefinitionData))continue;
        bool Updated=false;
        for(const TCHAR* Key:{TEXT("icon"),TEXT("ue_icon"),TEXT("rarity"),TEXT("grade")})
        {
            if(Material&&FString(Key)!=TEXT("rarity")&&FString(Key)!=TEXT("grade"))continue;
            if(!Material&&FString(Key)==TEXT("grade"))continue;
            FString NewIcon,OldIcon;CurrentData->TryGetStringField(Key,OldIcon);
            if(DefinitionData->TryGetStringField(Key,NewIcon)&&!NewIcon.IsEmpty()&&OldIcon!=NewIcon){CurrentData->SetStringField(Key,NewIcon);Updated=true;}
        }
        if(Updated){I.Data.Empty();FJsonSerializer::Serialize(CurrentData.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Removed=true;}
    }
    Removed = NormalizeBowState(Clean) || Removed;
    NormalizeProductionState(Clean);
    const auto Previous=Snapshot();bPersistenceBlocked=false;
    // Commit through the checked A/B transaction; never reset the player's save.
    if(Removed){Publish(Best->Profile);if(!CommitState(Clean)){Publish(Previous);bPersistenceBlocked=true;return false;}}
    else Publish(Clean);
    ApplyToPawn();
    if(CurrentPawn.IsValid())UProgressiveInfectionComponent::GetOrAdd(CurrentPawn.Get())->Restore(Current.Infection);
    RefreshDrops();OnChanged.Broadcast();
    if(RecoveredGroundAmmo>0)PostNotice(TEXT("旧版地面弹药已回收"),FString::Printf(TEXT("%lld 发已计入弹药袋"),RecoveredGroundAmmo));
    return true;
}
bool UColdSteelStatusModel::SaveNow()
{
    SyncRuntime();
    // Saving captures the live weapon; it is not an equipment command. Keep the
    // checked transaction and UI publication without reapplying the pawn to itself.
    return PersistState(Snapshot(),false);
}
int64 UColdSteelStatusModel::MaxExperience()const{return(20ll+Level*20ll+int64(Level)*Level*12)*8;}
bool UColdSteelStatusModel::GainExperience(int64 Amount)
{
    if(Amount<=0||Amount>1000000000000ll)return false;SyncRuntime();auto P=Snapshot();P.Experience+=FMath::FloorToInt64(Amount*TributeEffect(TEXT("expPercent")));
    while(P.Level<10000){int64 Need=(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8;if(P.Experience<Need)break;P.Experience-=Need;++P.Level;P.Points=FMath::Min(P.Points+3,1000000);}
    if(P.Level==10000)P.Experience=FMath::Min(P.Experience,(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8-1);
    return CommitState(P);
}
bool UColdSteelStatusModel::AwardKill(AActor* Victim,int64 Reward)
{
    if(!Victim||RewardedVictims.Contains(Victim)||Reward<=0||Reward>1000000000)return false;
    if(ActiveFireballRewards && ActiveFireballRewards->Victim==Victim){ActiveFireballRewards->Kills.FindOrAdd(Victim)=Reward;return true;}
    SyncRuntime();auto P=Snapshot();if(!DungeonLayout::RecordKill(P.DungeonRun,Victim))return false;P.Kills=FMath::Min(P.Kills+1,MAX_int32-1);
    // 2026-09-23 迁移原 exp-system.js/goldDrop：经验按玩家与怪物配置等级的压级/越级倍率
    // （未注册目标恒 1，行为不变），金币按 等级×4+随机1..10、全局×.5、rank elite2/lord3。
    P.Experience+=FMath::FloorToInt64(MonsterCoreStats::ScaleKillExperience(Victim,Level,Reward)*TributeEffect(TEXT("expPercent")));
    if(const int64 Gold=MonsterCoreStats::RollKillGold(Victim))
    {
        auto Item=CreateItem(TEXT("gold"),Gold);
        if(!Item.Data.IsEmpty()&&!ColdSteelInventory::Insert(P.Items,Item))
        {
            Item.Place=2;Item.Cell=-1;Item.BackpackCell=-1;
            Item.Map=UGameplayStatics::GetCurrentLevelName(this,true);
            Item.Position=Victim->GetActorLocation()+FVector(0,0,12);
            P.Items.Add(MoveTemp(Item));
        }
    }
    if(ActiveTrainingHit && ActiveTrainingHit->Victim==Victim && ActiveTrainingHit->bEligible)
    {
        ActiveTrainingHit->bKillAttempted=true;
        if(!ActiveTrainingHit->SkillId.IsNone())
        {
            const auto& Skill=MasteryDefinition(ActiveTrainingHit->SkillId);
            ColdSteelSkills::AddExperience(P,Skill,Skill.KillExperience+Skill.HitExperience+ActiveTrainingHit->ExtraExperience+(ActiveTrainingHit->bCritical?Skill.CriticalExperience:0));
        }
        if(ActiveTrainingHit->bCritical)ColdSteelSkills::AddExperience(P,CriticalStrikeSkill,CriticalStrikeSkill.CriticalHitExperience+CriticalStrikeSkill.CriticalKillExperience);
        if(ActiveTrainingHit->bMelee)ColdSteelSkills::AddExperience(P,DexterousHandsSkill,DexterousHandsSkill.MeleeKillExperience+DexterousHandsSkill.MeleeHitExperience);
    }
    while(P.Level<10000){int64 Need=(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8;if(P.Experience<Need)break;P.Experience-=Need;++P.Level;P.Points=FMath::Min(P.Points+3,1000000);}
    if(P.Level==10000)P.Experience=FMath::Min(P.Experience,(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8-1);
    // 击杀奖励先落在实时档案里，写盘交给定时自动存档；升级仍走即时带校验事务。
    if(!StageTraining(MoveTemp(P)))return false;RewardedVictims.Add(Victim);
    // 白玉/人参献祭：击杀后 1 秒内回复 maxHp×(killHpHealPercent-1) 与 maxMp×(killMpHealPercent-1)。
    if(const double HpRatio=TributeEffect(TEXT("killHpHealPercent"))-1;HpRatio>0)
        if(auto* H=CurrentPawn.Get()?CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr)if(!H->IsDead())
        {KillProcHp+=H->MaxHealth*HpRatio;KillProcTime=1;if(auto* S=UCombatStatusFormula::GetOrAdd(CurrentPawn.Get()))S->ShowProcTile(TEXT("marbleHeal"),1);}
    if(const double MpRatio=TributeEffect(TEXT("killMpHealPercent"))-1;MpRatio>0)
        if(CurrentPawn.IsValid()){KillProcMp+=Derived(TEXT("maxMp"))*MpRatio;KillProcTime=1;if(auto* S=UCombatStatusFormula::GetOrAdd(CurrentPawn.Get()))S->ShowProcTile(TEXT("ginsengHeal"),1);}
    return true;
}
const FColdSteelItem* UColdSteelStatusModel::FindItem(const FString& Id)const{return Current.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Id;});}
const FColdSteelItem* UColdSteelStatusModel::Equipped(int32 S)const{int32 N=Owner(Current.Items,1,S<0?Current.ActiveWeaponSlot:S);return N>=0?&Current.Items[N]:nullptr;}
bool UColdSteelStatusModel::CycleWeapon(){if(!Current.ActiveProductionTool.IsEmpty())return StowProductionTool();SyncRuntime();auto P=Snapshot();int32 Other=P.ActiveWeaponSlot==6?9:6;if(Owner(P.Items,1,Other)<0){Message=TEXT("另一组武器槽为空");return false;}P.ActiveWeaponSlot=Other;return CommitState(P);}
FColdSteelItem UColdSteelStatusModel::CreateItem(const FString& Def,int64 Count)const
{
    FColdSteelItem I;I.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);I.Definition=Def;I.Count=Count;
    if(const FString* Data=Definitions.Find(Def))I.Data=*Data;
    I.LoadedAmmoType=AmmoGroupFor(I);
    I.Magazine=(IsMeleeWeapon(I)||IsBow(I))?0:Number(I,TEXT("gunsmith_base_mag"),30);
    if(IsMeleeWeapon(I)||IsBow(I))I.Reserve=0;
    I.StackMax=Number(I,TEXT("maxStack"),Number(I,TEXT("stack_max"),1));
    if(Def==TEXT("reforge_ticket"))I.StackMax=9999;
    if(Text(I,TEXT("category"))==TEXT("gold"))I.StackMax=9007199254740991ll;
    const auto Size=Footprint(I);I.Width=Size.X;I.Height=Size.Y;
    return I;
}
FColdSteelProposal UColdSteelStatusModel::ProposeMove(const FString& Id,int32 Place,int32 Cell,int32 Orientation)const{const auto* I=FindItem(Id);if(Place==4||(I&&I->Place==4))return ProposeWarehouse(Id,Place,Cell,Orientation);auto P=ColdSteelInventory::Move(Current.Items,Id,Place,Cell,Orientation);P.Revision=Current.Generation;return P;}
bool UColdSteelStatusModel::CommitProposal(const FColdSteelProposal& R){if(!R.bValid){Message=R.Reason;return false;}if(R.Revision!=Current.Generation){Message=TEXT("物品已变化，请重新拖动");return false;}auto P=Snapshot();P.Items=R.Items;if(R.ActiveWeaponSlot>=0){P.ActiveWeaponSlot=R.ActiveWeaponSlot;P.ActiveProductionTool.Reset();}return CommitState(P);}
bool UColdSteelStatusModel::MoveItem(const FString& Id,int32 Place,int32 Cell,int32 Orientation){SyncRuntime();return CommitProposal(ProposeMove(Id,Place,Cell,Orientation));}
bool UColdSteelStatusModel::AddItem(const FString& Def,int64 Count){if(AmmoType(Def))return GrantAmmo(Def,Count);if(Count<=0||Count>9007199254740991ll||!Definitions.Contains(Def))return false;SyncRuntime();auto P=Snapshot();if(!Insert(P.Items,CreateItem(Def,Count))){Message=TEXT("背包空间不足");return false;}return CommitState(P);}
bool UColdSteelStatusModel::Split(const FString& Id,int64 Count)
{
    SyncRuntime();auto P=Snapshot();auto* I=P.Items.FindByPredicate([&](const auto& V){return V.InstanceId==Id;});
    if(!I||(I->Place!=0&&I->Place!=4)||Count<=0||Count>=I->Count||Text(*I,TEXT("category"))==TEXT("gold"))return false;
    auto Part=*I;Part.InstanceId=FGuid::NewGuid().ToString(EGuidFormats::Digits);Part.Count=Count;int32 Cell=-1;
    const int32 Capacity=I->Place==4?WarehouseCapacity():72; // 储物箱按自身会话容量找空位
    const int32 Start=I->Place==4?(I->Cell/ColdSteelWarehouse::CellsPerPage)*ColdSteelWarehouse::CellsPerPage:0;
    for(int32 N=0;N<Capacity;++N){const int32 C=(Start+N)%Capacity;if(I->Place==4?ColdSteelWarehouse::Fits(P.Items,Part,C,Capacity):Fits(P.Items,Part,C)){Cell=C;break;}}
    if(Cell<0){Message=TEXT("没有连续空间拆分，原数量保留");return false;}
    I->Count-=Count;Part.Cell=Cell;P.Items.Add(Part);if(!CommitState(P))return false;
    if(Part.Place==4&&WarehousePage!=Cell/ColdSteelWarehouse::CellsPerPage){WarehousePage=Cell/ColdSteelWarehouse::CellsPerPage;Message=TEXT("已拆分，并切换到新堆叠所在页");OnChanged.Broadcast();}
    return true;
}
bool UColdSteelStatusModel::Sort()
{
    SyncRuntime();auto P=Snapshot();TArray<FColdSteelItem> Bag;for(const auto& I:P.Items)if(I.Place==0)Bag.Add(I);P.Items.RemoveAll([](const auto& I){return I.Place==0;});
    Bag.Sort([](const auto&A,const auto&B){if(A.Width*A.Height!=B.Width*B.Height)return A.Width*A.Height>B.Width*B.Height;return Text(A,TEXT("category"))+Text(A,TEXT("name"))+A.InstanceId<Text(B,TEXT("category"))+Text(B,TEXT("name"))+B.InstanceId;});
    // Sort preserves stack instances (the source pack contract does not merge them).
    for(auto I:Bag){int32 C=-1;for(int32 N=0;N<72;++N)if(Fits(P.Items,I,N)){C=N;break;}if(C<0){Message=TEXT("无法整理，原布局保留");return false;}I.Cell=C;P.Items.Add(I);}return CommitState(P);
}
bool UColdSteelStatusModel::BindHotbar(int32 Index,const FString& Id){return Index>=0&&Index<4&&BindQuickItem(Index+ColdSteelQuickBar::ItemOffset,Id);}
bool UColdSteelStatusModel::SwapHotbar(int32 A,int32 B){return A>=0&&A<4&&B>=0&&B<4&&SwapQuickBindings(A+ColdSteelQuickBar::ItemOffset,B+ColdSteelQuickBar::ItemOffset);}
const FColdSteelItem* UColdSteelStatusModel::ResolveHotbar(int32 Index)const{return Index>=0&&Index<4?ResolveQuickItem(Index+ColdSteelQuickBar::ItemOffset):nullptr;}
bool UColdSteelStatusModel::UseHotbar(int32 Index){return Index>=0&&Index<4&&UseQuickBinding(Index+ColdSteelQuickBar::ItemOffset);}
bool UColdSteelStatusModel::UseItem(const FString& Id)
{
    if(const auto* Tool=FindItem(Id);Tool&&Text(*Tool,TEXT("category"))==TEXT("tool"))return ToggleProductionTool(Id);
    SyncRuntime();auto P=Snapshot();int32 N=P.Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id;});if(N<0||P.Items[N].Place!=0)return false;
    auto& I=P.Items[N];if(I.Cooldown>0){Message=TEXT("物品冷却中");return false;}
    TSharedPtr<FJsonObject> O;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),O);const TSharedPtr<FJsonObject>* Effect=nullptr;
    if(!O||!O->TryGetObjectField(TEXT("useEffect"),Effect)||!CurrentPawn.IsValid()){Message=TEXT("该物品当前无法使用");return false;}
    auto Num=[&](const TCHAR* K){double V=0;(*Effect)->TryGetNumberField(K,V);return V;};
    auto* Health=CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>();if(!Health||Health->IsDead())return false;
    const float HP=Num(TEXT("hp"))+Health->MaxHealth*Num(TEXT("maxHpPercent"))*.01;
    const float MP=Num(TEXT("mp"))+Derived(TEXT("maxMp"))*Num(TEXT("maxMpPercent"))*.01;
    if((HP<=0||P.Health>=Health->MaxHealth)&&(MP<=0||Mana()>=Derived(TEXT("maxMp")))){Message=TEXT("当前资源已满或效果不可用");return false;}
    P.Health=FMath::Clamp(P.Health+FMath::Max(0.f,HP),0.f,Health->MaxHealth);P.Mana=FMath::Clamp(P.Mana+FMath::Max(0.f,MP),0.f,Derived(TEXT("maxMp")));
    I.Cooldown=Number(I,TEXT("useCooldown"));if(--I.Count<=0)P.Items.RemoveAt(N);return CommitState(P);
}
bool UColdSteelStatusModel::DefaultAction(const FString& Id)
{
    const auto* Found=FindItem(Id);if(!Found)return false;const auto I=*Found;
    if(I.Place==4)return TransferWarehouse(Id,0);
    if(bWarehouseOpen&&(I.Place==0||I.Place==1))return TransferWarehouse(Id,4);
    if(I.Place==1)return MoveItem(Id,0,-1);
    if(Text(I,TEXT("category"))==TEXT("consumable")||(Text(I,TEXT("category"))==TEXT("tool")&&!IsEquippedProductionTool(I)))return UseItem(Id);
    for(int32 S=0;S<15;++S)if(CanEquip(I,S)&&!Equipped(S)&&!Locked(Current.Items,S))return MoveItem(Id,1,S);
    for(int32 S=0;S<15;++S)if(CanEquip(I,S)&&!Locked(Current.Items,S))return MoveItem(Id,1,S);
    Message=TEXT("该物品不能穿戴或使用");return false;
}
void UColdSteelStatusModel::SyncRuntime()
{
    if(!CurrentPawn.IsValid() || CurrentPawn->IsResolvingActionInterrupt())return;
    const auto* Dual=CurrentPawn->FindComponentByClass<UPistolDualWieldComponent>();
    const bool DualActive=Dual && Dual->IsActive();
    if(DualActive)Dual->SyncInventory(Current.Items);
    if(auto* H=CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>())Current.Health=H->Health;
    if(const auto* Infection=CurrentPawn->FindComponentByClass<UProgressiveInfectionComponent>())Current.Infection=Infection->GetState();
    // Dual hand counters are authoritative even inside a synchronous hit/reward
    // callback, before the character's main-hand display cache has been updated.
    if(!DualActive)for(auto& I:Current.Items)if(I.Place==1&&I.Cell==Current.ActiveWeaponSlot&&!IsMeleeWeapon(I))
    {
        I.VirtualMagazineAmmo=FMath::Clamp(I.VirtualMagazineAmmo-FMath::Max(0,I.Magazine-CurrentPawn->GetMagazineAmmo()),0,CurrentPawn->GetMagazineAmmo());
        I.Magazine=CurrentPawn->GetMagazineAmmo();
        if(I.Definition==TEXT("ue_dan_wesson715") && Number(I,TEXT("revolver_case_count"),-1)!=CurrentPawn->GetRevolverCaseCount())
        {
            StoreRevolverCaseCount(I,CurrentPawn->GetRevolverCaseCount());
        }
    }
    for(TActorIterator<AColdSteelPickup> It(GetWorld());It;++It)if(auto* I=Current.Items.FindByPredicate([&](const auto& V){return V.InstanceId==It->ItemId&&V.Place==2;})){I->Position=It->GetActorLocation();I->WorldRotation=It->GetActorRotation();}
}
void UColdSteelStatusModel::ApplyToPawn(){if(CurrentPawn.IsValid())CurrentPawn->ApplyColdSteelProfile(this);}
void UColdSteelStatusModel::AttachPawn(AFPSGAMECharacter* Pawn)
{
    CurrentPawn=Pawn;
    if(Current.Health<=0){Current.Infection=FInfectionState{};Current.Health=Derived(TEXT("maxHp"));Current.Stamina=MaxStamina();Current.StaminaRecoveryDelay=0;Current.bSprintExhausted=false;}
    ApplyToPawn();
    if(Pawn)UProgressiveInfectionComponent::GetOrAdd(Pawn)->Restore(Current.Infection);
    RefreshDrops();OnStaminaChanged.Broadcast();
}
void UColdSteelStatusModel::ReduceAllAbilityCooldowns(float Seconds)
{
    if(Seconds<=0.f)return;
    // Mirrors the TickRuntime decrement: reserved casts have not started their clock
    // yet, so only running cooldowns shrink (2D rune-sword contract, 0.5 s per event).
    if(!Current.bFireballReserved)Current.FireballCooldown=FMath::Max(0.f,Current.FireballCooldown-Seconds);
    if(!Current.bIceSpikeReserved)Current.IceSpikeCooldown=FMath::Max(0.f,Current.IceSpikeCooldown-Seconds);
    Current.LightningCooldown=FMath::Max(0.f,Current.LightningCooldown-Seconds);
    Current.HolyLightCooldown=FMath::Max(0.f,Current.HolyLightCooldown-Seconds);
    Current.MeteorCooldown=FMath::Max(0.f,Current.MeteorCooldown-Seconds);
    Current.FlameArmorCooldown=FMath::Max(0.f,Current.FlameArmorCooldown-Seconds);
    if(!Current.bQuickCombatReserved)Current.QuickCombatCooldown=FMath::Max(0.f,Current.QuickCombatCooldown-Seconds);
    Current.WhirlwindCooldown=FMath::Max(0.f,Current.WhirlwindCooldown-Seconds);
    if(CurrentPawn.IsValid())
        if(auto* Blades=CurrentPawn->FindComponentByClass<URuneOrbBladesComponent>())Blades->ReduceCooldown(Seconds);
}

void UColdSteelStatusModel::TickRuntime(float Delta,AFPSGAMECharacter* Pawn)
{
    if(Pawn!=CurrentPawn.Get())return;for(auto& I:Current.Items)I.Cooldown=FMath::Max(0.f,I.Cooldown-Delta);
    if(HasNoAbilityCooldown())Current.FireballCooldown=0.f;
    else if(!Current.bFireballReserved)Current.FireballCooldown=FMath::Max(0.f,Current.FireballCooldown-Delta);
    if(HasNoAbilityCooldown())Current.IceSpikeCooldown=0.f;
    else if(!Current.bIceSpikeReserved)Current.IceSpikeCooldown=FMath::Max(0.f,Current.IceSpikeCooldown-Delta);
    Current.LightningCooldown=HasNoAbilityCooldown()?0.f:FMath::Max(0.f,Current.LightningCooldown-Delta);
    Current.HolyLightCooldown=HasNoAbilityCooldown()?0.f:FMath::Max(0.f,Current.HolyLightCooldown-Delta);
    Current.MeteorCooldown=HasNoAbilityCooldown()?0.f:FMath::Max(0.f,Current.MeteorCooldown-Delta);
    Current.FlameArmorCooldown=HasNoAbilityCooldown()?0.f:FMath::Max(0.f,Current.FlameArmorCooldown-Delta);
    if(HasNoAbilityCooldown())Current.QuickCombatCooldown=0.f;
    else if(!Current.bQuickCombatReserved)Current.QuickCombatCooldown=FMath::Max(0.f,Current.QuickCombatCooldown-Delta);
    if(HasNoAbilityCooldown())Current.WhirlwindCooldown=0.f;
    else Current.WhirlwindCooldown=FMath::Max(0.f,Current.WhirlwindCooldown-Delta);
    TickFormulaBuffs(Delta);
    TickStamina(Delta,Pawn);
    if(Delta>0)if(auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&!Health->IsDead()){
        Current.Mana=FMath::Clamp(Current.Mana+Derived(TEXT("mpRegen"))*Delta,0.f,Derived(TEXT("maxMp")));
        Health->Health=FMath::Min(Health->MaxHealth,Health->Health+Derived(TEXT("hpRegen"))*Delta);Current.Health=Health->Health;
        // 白玉/人参击杀回复：KillProc* 按 1 秒窗口折算成每秒量，窗口内步进结清。
        if(KillProcTime>0){const float Step=FMath::Min(Delta,KillProcTime);KillProcTime-=Step;
            Health->Health=FMath::Min(Health->MaxHealth,Health->Health+KillProcHp*Step);Current.Health=Health->Health;
            Current.Mana=FMath::Clamp(Current.Mana+KillProcMp*Step,0.f,Derived(TEXT("maxMp")));}
    }
    TickTreeGrowthClock(Delta);
    // 修行经验与击杀奖励已经落在实时档案里（StageTraining），这里只负责把「有未写盘增量」的档案
    // 按可配置周期落盘一次；没有增量就不空写。旧口径的 1 秒补写与无条件 5 秒写盘见文件顶部的说明。
    const float AutosaveSeconds=SaveAutosaveSeconds.GetValueOnGameThread();
    if(AutosaveSeconds>0.f)
    {
        SaveAccumulator+=Delta;
        if(SaveAccumulator>=AutosaveSeconds){SaveAccumulator=0;if(bTrainingDirty)SaveNow();}
    }
}
FString UColdSteelStatusModel::AmmoDefinition()const{const auto* I=Equipped();return I?AmmoDefinitionFor(*I):FString();}
int32 UColdSteelStatusModel::AmmoCount()const{return Equipped()?int32(FMath::Min<int64>(PouchCount(AmmoDefinition()),MAX_int32)):0;}
int32 UColdSteelStatusModel::ConsumeAmmo(int32 Requested, bool bCompletedReload, bool bReloadStep, int32 NeedsCycle)
{
    if(Requested<=0||!CurrentPawn.IsValid()||!Equipped()||!CurrentPawn->HasInventoryWeapon())return 0;
    SyncRuntime();Requested=FMath::Min(Requested,CurrentPawn->GetMagazineCapacity()-CurrentPawn->GetMagazineAmmo());if(Requested<=0)return 0;
    // Each range insertion may refill without creating inventory stacks. Only
    // the last insertion grants training, in the same successful save as ammo.
    const bool Infinite=(bCompletedReload||bReloadStep)&&CurrentPawn->HasInfiniteReserveAmmo();
    auto P=Snapshot();FString Def=AmmoDefinition();
    const int32 Taken=Infinite?Requested:int32(FMath::Min<int64>(Requested,P.AmmoPouch.FindRef(Def)));
    if(!Infinite)P.AmmoPouch.FindOrAdd(Def)-=Taken;
    for(auto& I:P.Items)if(I.Place==1&&I.Cell==P.ActiveWeaponSlot)
    {
        I.Magazine+=Taken;
        if(Taken>0 && !WeaponReloadStages::SetNeedsCycle(I,NeedsCycle))return 0;
        if(Infinite)I.VirtualMagazineAmmo+=Taken;
        if(I.Definition==TEXT("ue_dan_wesson715"))
        {
            StoreRevolverCaseCount(I,bReloadStep?FMath::Max(I.Magazine,CurrentPawn->GetRevolverCaseCount()):I.Magazine);
        }
    }
    if(Taken>0&&bCompletedReload)ColdSteelSkills::AddExperience(P,DexterousHandsSkill,DexterousHandsSkill.ReloadExperience);
    return Taken>0&&CommitState(P)?Taken:0;
}
bool UColdSteelStatusModel::ClearRevolverSpentCases(bool bDiscardLiveRounds)
{
    if (!CurrentPawn.IsValid() || !CurrentPawn->HasInventoryWeapon() || !Equipped()
        || Equipped()->Definition != TEXT("ue_dan_wesson715")) return false;
    const int32 RetainedRounds = bDiscardLiveRounds ? 0 : CurrentPawn->GetMagazineAmmo();
    if (CurrentPawn->GetRevolverCaseCount() == RetainedRounds
        && CurrentPawn->GetMagazineAmmo() == RetainedRounds) return true;
    SyncRuntime();
    auto P = Snapshot();
    for (auto& I : P.Items) if (I.Place == 1 && I.Cell == P.ActiveWeaponSlot)
    {
        // A speedloader discards live rounds at extraction. Save the loss with
        // the cleared cases; do not refund reserves or grant reload experience.
        if (bDiscardLiveRounds) I.Magazine = 0;
        I.VirtualMagazineAmmo=FMath::Min(I.VirtualMagazineAmmo,I.Magazine);
        StoreRevolverCaseCount(I, I.Magazine);
        return CommitState(P);
    }
    return false;
}
bool UColdSteelStatusModel::Drop(const FString& Id)
{
    if(!CurrentPawn.IsValid())return false;SyncRuntime();auto P=Snapshot();auto* I=P.Items.FindByPredicate([&](const auto& V){return V.InstanceId==Id;});if(!I||(I->Place>1&&!(I->Place==4&&bWarehouseOpen)))return false;
    const FVector Origin=CurrentPawn->GetActorLocation();
    FVector Candidate=Origin+CurrentPawn->GetActorForwardVector()*120;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(InventoryGroundDrop),false,CurrentPawn.Get());
    FHitResult Obstacle,Ground;
    if(GetWorld()->SweepSingleByChannel(Obstacle,Origin,Candidate,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(45),Query))Candidate=Obstacle.Location-CurrentPawn->GetActorForwardVector()*2;
    auto FindGround=[&](FVector At){return GetWorld()->LineTraceSingleByChannel(Ground,At+FVector(0,0,40),At-FVector(0,0,500),ECC_Visibility,Query)&&Ground.ImpactNormal.Z>=.5f&&FVector::Dist(Origin,Ground.ImpactPoint)<=230;};
    if(!FindGround(Candidate)&&!FindGround(Origin)){Message=TEXT("附近没有可放置物品的地面");return false;}
    // Release above the ground; the rigid body resolves the fall and landing.
    I->Place=2;I->Map=UGameplayStatics::GetCurrentLevelName(this,true);I->Position=Ground.ImpactPoint;I->Position.Z=FMath::Max(Ground.ImpactPoint.Z+60,Origin.Z+15);
    I->WorldRotation=FRotator(5,CurrentPawn->GetActorRotation().Yaw,-65);
    StampProductionDrop(*I);
    const double Begin=FPlatformTime::Seconds();if(!CommitState(P))return false;const double Saved=FPlatformTime::Seconds();RefreshDrops();
    if(bAudit)UE_LOG(LogTemp,Display,TEXT("DropTiming: save %.3f ms spawn %.3f ms"),(Saved-Begin)*1000,(FPlatformTime::Seconds()-Saved)*1000);return true;
}
bool UColdSteelStatusModel::Pickup(const FString& Id)
{
    if(!CurrentPawn.IsValid())return false;
    AColdSteelPickup* Target=nullptr;for(TActorIterator<AColdSteelPickup> It(GetWorld());It;++It)if(It->ItemId==Id&&It->CanInteract(CurrentPawn.Get())){Target=*It;break;}
    if(!Target)return false;SyncRuntime();auto P=Snapshot();int32 N=P.Items.IndexOfByPredicate([&](const auto&I){return I.InstanceId==Id&&I.Place==2;});
    if(N<0||P.Items[N].Map!=UGameplayStatics::GetCurrentLevelName(this,true)||FVector::Dist(CurrentPawn->GetActorLocation(),P.Items[N].Position)>250)return false;
    auto I=P.Items[N];P.Items.RemoveAt(N);if(AmmoType(I.Definition)){if(!AddAmmoToState(P,I.Definition,I.Count))return false;}else if(!Insert(P.Items,I)){Message=TEXT("背包已满，物品留在地面");return false;}if(!CommitState(P))return false;RefreshDrops();return true;
}
void UColdSteelStatusModel::RefreshDrops()
{
    if(!GetWorld()||!CurrentPawn.IsValid())return;TSet<FString> Existing;
    for(TActorIterator<AColdSteelPickup> It(GetWorld());It;++It){const auto* I=FindItem(It->ItemId);if(!I||I->Place!=2)It->Destroy();else Existing.Add(It->ItemId);}
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    // Harvest drops stream independently with a world GUID, range and spawn budget.
    for(const auto& I:Current.Items)if(I.Place==2&&!I.HarvestWorldId.IsValid()&&I.Map==Map&&!Existing.Contains(I.InstanceId)){FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;auto* A=GetWorld()->SpawnActor<AColdSteelPickup>(I.Position,I.WorldRotation,Spawn);if(A)A->InitializeItem(I);}
}
