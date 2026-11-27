#include "../Movement/StableHorseGear.h"
#include "../Weapons/MagicCrystalMana.h"
#include "../Skills/ColdSteelSkillTree.h"
#include "../Dungeon/DungeonLayout.h"
#include "../Weapons/JingangRuneComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelProfilePersistence.h"
#include "ColdSteelIncineratorStorage.h"
#include "../Skills/FPSMagicArrowRainComponent.h"
#include "../Skills/FPSElementalArrowComponent.h"
#include "ColdSteelContainerSearchSubsystem.h"
#include "GameFramework/PlayerController.h"
#include "ColdSteelProfileRecovery.h"
#include "../Items/FoodSpoilage.h"
#include "../Items/CampfireFoodCatalog.h"
#include "ColdSteelCurrency.h"
#include "ColdSteelItemRarity.h"
#include "../Items/FPSPotionUseComponent.h"
#include "../Weapons/WeaponReloadStages.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/RuneOrbBladesComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
#include "ColdSteelPickup.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCoreStats.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "EngineUtils.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/FrostSwordRunes.h"
#include "Misc/SecureHash.h"


using namespace ColdSteelInventory;
namespace ColdSteelProfilePersistence
{
// Catalog-owned tuning must also reach guest shadows and returned loot. Local
// disk migration alone leaves old sniper/machine-gun copies on stale mastery,
// movement and crit rules after reconnect or an inventory mirror.
void RefreshWeaponTuning(FColdSteelProfile& State,const TMap<FString,FString>& Definitions)
{
    for(auto& Item:State.Items)
    {
        // 枪械的类别、暴击与非枪械的固有要害/穿甲都按目录调校；旧实例缺项时读 0，
        // 会把 M1911 的要害特化、Viper 的穿甲和狙击的弱点收益整段吞掉。
        if(Item.Definition!=TEXT("ue_svd")&&Item.Definition!=TEXT("ue_svch")&&Item.Definition!=TEXT("ue_m24")
            &&Item.Definition!=TEXT("ue_m1911")&&Item.Definition!=TEXT("ue_pit_viper2011")
            &&Item.Definition!=TEXT("ue_m249")&&Item.Definition!=TEXT("ue_pkm_lowpoly")&&Item.Definition!=TEXT("ue_lmg201"))continue;
        const auto* Definition=Definitions.Find(Item.Definition);if(!Definition)continue;
        TSharedPtr<FJsonObject> Data,Catalog;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data
            ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Definition),Catalog)||!Catalog)continue;
        bool Changed=false;
        for(const TCHAR* Field:{TEXT("weaponType"),TEXT("weaponTypeTag")})
        {
            FString Value,Old;
            if(Catalog->TryGetStringField(Field,Value)&&(!Data->TryGetStringField(Field,Old)||Old!=Value))
            {Data->SetStringField(Field,Value);Changed=true;}
        }
        for(const TCHAR* Field:{TEXT("critDamageBonus"),TEXT("innate_weakpoint_percent"),TEXT("innate_armor_penetration")})
        {
            double Value=0.,Old=0.;
            if(Catalog->TryGetNumberField(Field,Value)&&(!Data->TryGetNumberField(Field,Old)||Old!=Value))
            {Data->SetNumberField(Field,Value);Changed=true;}
        }
        if(Changed){Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));}
    }
}
// Belt tuning belongs to the catalog, while enhancement level and placement
// belong to the instance. Apply the same migration before guest evaluation and
// owner receipts as local disk loading; never leave a guest on an old bonus.
void RefreshBeltTuning(FColdSteelProfile& State,const TMap<FString,FString>& Definitions)
{
    for(auto& Item:State.Items)
    {
        // Limit parsing to authored belts; profile mirrors also contain
        // large material inventories that do not need equipment migration.
        if(Item.Definition!=TEXT("ue_leather_quiver_belt")&&Item.Definition!=TEXT("ue_tactical_magazine_belt")
            &&Item.Definition!=TEXT("ue_melee_combat_belt")&&Item.Definition!=TEXT("ue_arcane_conduit_belt"))continue;
        const auto* Definition=Definitions.Find(Item.Definition);if(!Definition)continue;
        TSharedPtr<FJsonObject> Catalog,Data;FString Slot;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Definition),Catalog)||!Catalog
            ||!Catalog->TryGetStringField(TEXT("equipSlot"),Slot)||Slot!=TEXT("belt"))continue;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)continue;
        bool Changed=false;
        for(const TCHAR* Field:{TEXT("bonusStats"),TEXT("bonusPerEnhance"),TEXT("enhancement")})
        {
            const TSharedPtr<FJsonObject>* Current=nullptr;const TSharedPtr<FJsonObject>* Authored=nullptr;
            if(!Catalog->TryGetObjectField(Field,Authored)||!*Authored)continue;
            FString Expected,Previous;
            FJsonSerializer::Serialize((*Authored).ToSharedRef(),TJsonWriterFactory<>::Create(&Expected));
            if(Data->TryGetObjectField(Field,Current)&&*Current)
                FJsonSerializer::Serialize((*Current).ToSharedRef(),TJsonWriterFactory<>::Create(&Previous));
            if(Previous!=Expected)
            {
                // Catalog was parsed for this item, so no shared definition JSON
                // is exposed to subsequent instance processing.
                Data->SetObjectField(Field,*Authored);Changed=true;
            }
        }
        if(Changed){Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));}
    }
}
bool IsRetiredItem(const FString& Id)
{
    static const TSet<FString> Retired = {TEXT("fps_akm"),TEXT("fps_hk416"),TEXT("fps_m16"),TEXT("fps_akm_classic"),TEXT("fps_qbz191"),TEXT("fps_p9"),TEXT("ue_pkm"),TEXT("ue_pkm_a"),TEXT("ammo_762x54r"),TEXT("quartz")};
    return Retired.Contains(Id);
}
bool RemoveRetiredItems(FColdSteelProfile& P)
{
    const int32 ActiveIndex=Owner(P.Items,1,P.ActiveWeaponSlot);
    const bool RemovedActiveWeapon=ActiveIndex>=0&&IsRetiredItem(P.Items[ActiveIndex].Definition);
    TSet<FString> Removed;
    for (const auto& I : P.Items) if (IsRetiredItem(I.Definition)) Removed.Add(I.InstanceId);
    bool Changed = P.Items.RemoveAll([](const auto& I){ return IsRetiredItem(I.Definition); }) > 0;
    Changed |= P.ArmoryReceived.RemoveAll([](const FString& Id){ return IsRetiredItem(Id); }) > 0;
    // Retired quartz must not block discarding a previously paid frost-sword job.
    Changed |= P.ForgeJob.PaidMaterials.Remove(TEXT("quartz")) > 0;
    for (int32 N=0; N<P.Hotbar.Num(); ++N) {
        if (Removed.Contains(P.Hotbar[N]) || (P.HotbarDefinitions.IsValidIndex(N) && IsRetiredItem(P.HotbarDefinitions[N]))) {
            P.Hotbar[N].Reset(); if (P.HotbarDefinitions.IsValidIndex(N)) P.HotbarDefinitions[N].Reset(); Changed=true;
        }
    }
    // Clear the selected PKM family from saved quick bindings and its ammo pouch.
    for (auto& Binding : P.QuickBindings) {
        if (Removed.Contains(Binding.ItemId) || IsRetiredItem(Binding.ItemDefinition)) {
            Binding = FColdSteelQuickBinding(); Changed = true;
        }
    }
    Changed |= P.AmmoPouch.Remove(TEXT("ammo_762x54r")) > 0;
    // An intentionally selected empty loadout is a persistent unarmed state.
    // Only removal of its active retired weapon should select the other loadout.
    if (RemovedActiveWeapon) {
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
using namespace ColdSteelProfilePersistence;

// The save keeps only level plus the remainder inside that level. Add each
// crossed threshold back so the HUD reports the experience actually awarded,
// not the remainder left after a level-up.
int64 UColdSteelStatusModel::GainedCharacterExperience(const FColdSteelProfile& After) const
{
    int64 Gained=After.Experience-Current.Experience;
    for(int32 L=Current.Level;L<After.Level;++L)
        Gained+=(20ll+L*20ll+int64(L)*L*12)*8;
    return FMath::Max<int64>(0,Gained);
}


void UColdSteelStatusModel::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    RifleSkill=ColdSteelSkills::LoadDefinition();
    PistolSkill=ColdSteelSkills::LoadDefinition(TEXT("pistolMastery"));
    CriticalStrikeSkill=ColdSteelSkills::LoadDefinition(TEXT("criticalStrike"));
    FireballSkill=ColdSteelSkills::LoadDefinition(TEXT("fireball"));
    IceSpikeSkill=ColdSteelSkills::LoadDefinition(TEXT("iceSpike"));
    IceWallSkill=ColdSteelSkills::LoadDefinition(TEXT("iceWall"));
    BlizzardSkill=ColdSteelSkills::LoadDefinition(TEXT("blizzard"));
    LightningSkill=ColdSteelSkills::LoadDefinition(TEXT("lightningStrike"));
    StormDomainSkill=ColdSteelSkills::LoadDefinition(TEXT("stormDomain"));
    ThunderLanceSkill=ColdSteelSkills::LoadDefinition(TEXT("thunderLance"));
    HolyLightSkill=ColdSteelSkills::LoadDefinition(TEXT("holyLight"));
    MeteorSkill=ColdSteelSkills::LoadDefinition(TEXT("meteor"));
    FlameArmorSkill=ColdSteelSkills::LoadDefinition(TEXT("flameArmor"));
    IceArmorSkill=ColdSteelSkills::LoadDefinition(TEXT("iceArmor"));
    LightningHasteSkill=ColdSteelSkills::LoadDefinition(TEXT("lightningHaste"));
    DragonBreathSkill=ColdSteelSkills::LoadDefinition(TEXT("dragonBreath"));
    DodgeSkill=ColdSteelSkills::LoadDefinition(TEXT("dodge"));LoadStaminaTuning();
    DexterousHandsSkill=ColdSteelSkills::LoadDefinition(TEXT("dexterousHands"));
    QuickCombatSkill=ColdSteelSkills::LoadDefinition(TEXT("quickCombat"));
    RuneBladesSkill=ColdSteelSkills::LoadDefinition(TEXT("runeBlades"));
    StaffLightSkill=ColdSteelSkills::LoadDefinition(TEXT("staffLight"));
    ColdSteelSkills::Migrate(Current);ColdSteelSkillTree::Migrate(Current);
    FString Json; TSharedPtr<FJsonObject> Root;
    if(FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/items.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root))
        for(const auto& Pair:Root->Values){FString Data;FJsonSerializer::Serialize(Pair.Value->AsObject().ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Data));Definitions.Add(FString(*Pair.Key),Data);}
    LoadProductionDefinitions();LoadBowDefinitions();LoadStaffDefinitions();LoadAmmoCatalog();
    for(auto& Pair:Definitions)
    {
        FColdSteelItem Item;Item.Definition=Pair.Key;Item.Data=Pair.Value;
        if(ColdSteelItemRarity::Normalize(Item))Pair.Value=MoveTemp(Item.Data);
    }
    ColdSteelFood::RegisterCatalog(Definitions);
    SaveSlot=TEXT("ColdSteelPlayer"); FString Requested;
    bAudit=FString(FCommandLine::Get()).Contains(TEXT("Audit"));
    if(FParse::Value(FCommandLine::Get(),TEXT("ColdSteelProfile="),Requested)) {
        if(!Requested.IsEmpty()&&Requested.Len()<64&&!Requested.Contains(TEXT("/"))&&!Requested.Contains(TEXT("\\"))&&!Requested.Contains(TEXT("..")))SaveSlot=TEXT("ColdSteel_")+Requested;
        else bPersistenceBlocked=true;
    } else if(bAudit)SaveSlot=TEXT("ColdSteel_AuditSession");
    // Every PIE GameInstance gets its own durable sandbox, even when all
    // windows share one process/command line. Seed once without writing the source.
    if(const FWorldContext* Context=GetGameInstance()->GetWorldContext();Context&&Context->WorldType==EWorldType::PIE)
    {
        const FString SourceSlot=SaveSlot;
        SaveSlot+=FString::Printf(TEXT("_PIE_%d"),Context->PIEInstance);
        const bool HasSandbox=UGameplayStatics::DoesSaveGameExist(SaveSlot+TEXT("_A"),0)
            ||UGameplayStatics::DoesSaveGameExist(SaveSlot+TEXT("_B"),0);
        if(!HasSandbox)
        {
            bool HasSource=false,Seeded=false;
            const FGuid SandboxIdentity=FGuid::NewGuid();
            for(const TCHAR* S:{TEXT("_A"),TEXT("_B")})
            {
                const FString From=SourceSlot+S,To=SaveSlot+S;
                HasSource|=UGameplayStatics::DoesSaveGameExist(From,0);
                auto* Source=ReadCheckedProfile(From);if(!Source)continue;
                Source->Profile.NetworkProfileId=SandboxIdentity;
                TArray<uint8> Bytes;
                if(UGameplayStatics::SaveGameToMemory(Source,Bytes)&&UGameplayStatics::SaveDataToSlot(Bytes,To,0)
                    &&FFileHelper::SaveStringToFile(HashBytes(Bytes),*ChecksumPath(To)))Seeded=true;
            }
            if(HasSource&&!Seeded){bPersistenceBlocked=true;Message=TEXT("测试档案复制失败，原存档未修改");return;}
        }
        UE_LOG(LogTemp,Display,TEXT("NET_PROFILE_SANDBOX instance=%d slot=%s"),Context->PIEInstance,*SaveSlot);
    }
    for(FName Key:{FName("str"),FName("dex"),FName("intt"),FName("con"),FName("wis"),FName("luck")})Current.Attributes.Add(Key,10);
    Current.NetworkProfileId=FGuid::NewGuid();
    Current.Hotbar.SetNum(4);Current.HotbarDefinitions.SetNum(4);Current.WarehouseLayoutVersion=1;NormalizeStamina(Current);Publish(Current);
    const bool Exists=UGameplayStatics::DoesSaveGameExist(SaveSlot+TEXT("_A"),0)||UGameplayStatics::DoesSaveGameExist(SaveSlot+TEXT("_B"),0);
    if(Exists){if(ReloadProfile()){GrantStartingArmory();}return;}
    auto Seed=Snapshot();auto Weapon=CreateItem(TEXT("ue_m4a1"));Weapon.Place=1;Weapon.Cell=6;Seed.Items.Add(Weapon);
    Seed.Souls=200;Seed.SoulCurrencyVersion=1;
    for(const auto& Pair:TArray<TPair<FString,int64>>{{TEXT("hp_potion"),5},{TEXT("mp_potion"),3},{TEXT("ammo_556"),90},{TEXT("ammo_762"),90},{TEXT("ammo_127"),60}}) {
        if(AmmoType(Pair.Key)){AddAmmoToState(Seed,Pair.Key,Pair.Value);continue;}
        auto I=CreateItem(Pair.Key,Pair.Value); if(!I.Data.IsEmpty())Insert(Seed.Items,I);
    }
    for(int32 Index=0;Index<2;++Index){const FString Def=Index==0?TEXT("hp_potion"):TEXT("mp_potion");for(const auto& I:Seed.Items)if(I.Definition==Def){Seed.Hotbar[Index]=I.InstanceId;Seed.HotbarDefinitions[Index]=Def;break;}}
    if(CommitState(Seed)){GrantStartingArmory();}
}
void UColdSteelStatusModel::Deinitialize(){SaveNow();Super::Deinitialize();}
FColdSteelProfile UColdSteelStatusModel::Snapshot() const {auto P=Current;P.Name=CharacterName;P.Class=CharacterClass;P.Level=Level;P.Points=AttributePoints;P.Attributes=Attributes;return P;}
void UColdSteelStatusModel::Publish(const FColdSteelProfile& P){Current=P;++StatCacheVersion;CharacterName=P.Name;CharacterClass=P.Class;Level=P.Level;AttributePoints=P.Points;Attributes=P.Attributes;bTrainingDirty=false;TrainingFlushAccumulator=0.f;OnStaminaChanged.Broadcast();}
UColdSteelStatusModel* UColdSteelStatusModel::CreateEquipmentModel(const FColdSteelProfile& Profile)
{
    UColdSteelStatusModel* Shadow=NewObject<UColdSteelStatusModel>(GetGameInstance()); // 子系统类 ClassWithin=UGameInstance：Outer 必须是 GameInstance，TransientPackage 会撞 UObjectGlobals 断言
    // 只读目录状态整体复制：物品定义、武器弹药分组、弹药目录、体力调参、技能定义（全字段随本实例目录走）。
    Shadow->Definitions=Definitions;
    Shadow->WeaponAmmoGroups=WeaponAmmoGroups;
    Shadow->AmmoTypes=AmmoTypes;
    Shadow->StaminaTuning=StaminaTuning;
    Shadow->DodgeSkill=DodgeSkill;
    Shadow->DexterousHandsSkill=DexterousHandsSkill;
    Shadow->RifleSkill=RifleSkill;
    Shadow->PistolSkill=PistolSkill;
    Shadow->CriticalStrikeSkill=CriticalStrikeSkill;
    Shadow->FireballSkill=FireballSkill;
    Shadow->IceSpikeSkill=IceSpikeSkill;
    Shadow->IceWallSkill=IceWallSkill;
    Shadow->BlizzardSkill=BlizzardSkill;
    Shadow->LightningSkill=LightningSkill;
    Shadow->StormDomainSkill=StormDomainSkill;
    Shadow->ThunderLanceSkill=ThunderLanceSkill;
    Shadow->HolyLightSkill=HolyLightSkill;
    Shadow->MeteorSkill=MeteorSkill;
    Shadow->FlameArmorSkill=FlameArmorSkill;
    Shadow->IceArmorSkill=IceArmorSkill;
    Shadow->LightningHasteSkill=LightningHasteSkill;
    Shadow->DragonBreathSkill=DragonBreathSkill;
    Shadow->QuickCombatSkill=QuickCombatSkill;
    Shadow->RuneBladesSkill=RuneBladesSkill;
    Shadow->StaffLightSkill=StaffLightSkill;
    Shadow->Publish(Profile);
    Shadow->bPersistenceBlocked=true;
    Shadow->bNetShadowProfile=true;
    return Shadow;
}
UColdSteelStatusModel* UColdSteelStatusModel::CreateShadowModel(const FColdSteelProfile& GuestProfile)
{
    auto Migrated=GuestProfile;bool CurrencyChanged=false;FString CurrencyReason;
    RefreshWeaponTuning(Migrated,Definitions);
    RefreshBeltTuning(Migrated,Definitions);
    NormalizeStaffState(Migrated);
    RemoveRetiredItems(Migrated);
    if(!ColdSteelCurrency::Normalize(Migrated,CurrencyChanged,CurrencyReason))return nullptr;
    ColdSteelItemRarity::Normalize(Migrated.Items);
    ColdSteelProfileRecovery::InterruptedSpells(Migrated,float(ResourceMaximum(Migrated,true)));
    bool FootprintChanged=false;FString FootprintReason;
    if(!MigrateAuthoredGridFootprints(Migrated,FootprintChanged,FootprintReason))
    {Message=FootprintReason;return nullptr;}
    ColdSteelFood::RebaseProfile(Migrated,ColdSteelFood::Clock(this));
    return CreateEquipmentModel(Migrated);
}
void UColdSteelStatusModel::AdoptNetMirror(const FColdSteelProfile& External,bool AnnounceGains)
{
    auto Migrated=External;bool CurrencyChanged=false;FString CurrencyReason;
    if(GetWorld() && GetWorld()->GetNetMode()==NM_Client && Migrated.NetworkProfileId==Current.NetworkProfileId &&
        Current.MountRoster.Revision>Migrated.MountRoster.Revision)
    {
        auto NewerRoster=Current.MountRoster;
        if(Migrated.CampfireInventoryRevision>=Current.CampfireInventoryRevision)
            StableHorseGear::CopyEquipment(NewerRoster,Migrated.MountRoster);
        Migrated.MountRoster=MoveTemp(NewerRoster);
    }
    RefreshWeaponTuning(Migrated,Definitions);
    RefreshBeltTuning(Migrated,Definitions);
    NormalizeStaffState(Migrated);
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&Migrated.FoodClockId==Current.FoodClockId)
        Migrated.FoodClockDay=FMath::Max(Migrated.FoodClockDay,Current.FoodClockDay);
    RemoveRetiredItems(Migrated);
    if(!ColdSteelCurrency::Normalize(Migrated,CurrencyChanged,CurrencyReason)){Message=CurrencyReason;return;}
    ColdSteelItemRarity::Normalize(Migrated.Items);
    if(Migrated.CampfireInventoryRevision>Current.CampfireInventoryRevision)
    {
        // Reconnection may restore a committed destruction through a full mirror
        // with no surviving request/receipt. Retire bindings only for exact
        // instances removed by that newer authority inventory.
        TSet<FString> Removed;
        for(const auto& Item:Current.Items)
            if(!Item.Container.StartsWith(TEXT("NetView."))&&!Migrated.Items.ContainsByPredicate([&](const auto& I){return I.InstanceId==Item.InstanceId;}))
                Removed.Add(Item.InstanceId);
        for(auto& Binding:Migrated.QuickBindings)if(Removed.Contains(Binding.ItemId))Binding=FColdSteelQuickBinding();
        for(int32 N=0;N<Migrated.Hotbar.Num();++N)if(Removed.Contains(Migrated.Hotbar[N]))
        {Migrated.Hotbar[N].Reset();if(Migrated.HotbarDefinitions.IsValidIndex(N))Migrated.HotbarDefinitions[N].Reset();}
        if(Removed.Contains(Migrated.ActiveProductionTool))Migrated.ActiveProductionTool.Reset();
    }
    Migrated.MergeStarMarrowSpend(Current.StarMarrowManaSpent);
    Migrated.MergeOathStamina(Current.OathStaminaRestored,StaminaMaximum(Migrated,StaminaTuning));
    if(Migrated.MagicCrystalManaRestored<Current.MagicCrystalManaRestored)
        MagicCrystalMana::Merge(Migrated,Current.MagicCrystalManaRestored,float(ResourceMaximum(Migrated,true)));
    if(AnnounceGains)QueueAcquisitionNotices(Current,Migrated);
    Publish(Migrated);
}
bool UColdSteelStatusModel::CommitState(FColdSteelProfile State)
{
    auto* Pawn=RuntimePawn();
    auto* Search=!bStagingNetworkContainer&&Pawn&&Pawn->GetNetMode()==NM_Standalone?Pawn->GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>():nullptr;
    auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(Search&&!Search->IsActive(PC))Search=nullptr;
    if(Search&&!Search->ValidateChange(PC,Current.Items,State.Items,Message))return false;
    // Only successful inventory commits teach the depositor about newly inserted items.
    TArray<FColdSteelItem> Before;if(Search)Before=Current.Items;
    if(!PersistState(MoveTemp(State),true))return false;
    if(Search)Search->ObserveChange(PC,Before,Current.Items);
    return true;
}
bool UColdSteelStatusModel::CommitWorkshopCheckpoint(FColdSteelProfile State,const FString& GuestSlot)
{
    // Lesson acceptance and autonomous workpiece settlement share this path.
    // A staged workstation request owns its final journaled save and rollback.
    if(!bNetShadowProfile||IsStagingNetworkContainer())return CommitState(MoveTemp(State));
    auto* Pawn=RuntimePawn();
    const auto* Owner=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    if(!Owner||Owner->GetShadowModel()!=this||GuestSlot.IsEmpty()||Owner->CampfireGuestSlot()!=GuestSlot)
    {
        Message=TEXT("客机工坊档案尚未就绪，请稍后再试。");
        return false;
    }
    TGuardValue<FString> SlotGuard(CampfireGuestSaveSlot,GuestSlot);
    TGuardValue<bool> TransactionGuard(bSavingTransaction,true);
    return CommitState(MoveTemp(State));
}
bool UColdSteelStatusModel::CommitCampfireState(FColdSteelProfile State,const FString& WorldKey,const FString& GuestSlot)
{
    if(bNetShadowProfile&&GuestSlot.IsEmpty())return false;
    TGuardValue<FString> SlotGuard(CampfireGuestSaveSlot,GuestSlot);
    TGuardValue<bool> TransactionGuard(bSavingTransaction,true);
    State.CampfireInventoryRevision=Current.CampfireInventoryRevision+1;
    State.CampfireWorldReceipts.FindOrAdd(WorldKey)=State.CampfireInventoryRevision;
    return PersistState(MoveTemp(State),true);
}
bool UColdSteelStatusModel::SetPlayerAppearance(FName HeadId,FName HairId)
{
    if(Current.PlayerHeadId==HeadId&&Current.PlayerHairId==HairId)return true;
    auto Next=Snapshot();Next.PlayerHeadId=HeadId;Next.PlayerHairId=HairId;
    // A cosmetic change must not re-equip weapons or interrupt an active action.
    return PersistState(MoveTemp(Next),false);
}
bool UColdSteelStatusModel::PersistState(FColdSteelProfile State,bool bApplyPawn)
{
    if(bTransactionSaveUnconfirmed){Message=TEXT("交易保存结果待恢复，请保留存档并重启主机后恢复");return false;}
    if(bCampfireInventoryPending){Message=TEXT("联机物品操作正在同步，请稍候");return false;}
    // M2 联机：放开监听服/客户端的档案写入（各自写各自磁盘副本）；专用服拒绝（无本地玩家档案语义）。
    // Shadow gameplay transactions are authoritative in memory. Only their disk
    // writes are blocked: the PlayerState owns guest persistence and mirroring.
    if(bNetShadowProfile)
    {
        const auto* AuthorityPawn=RuntimePawn();
        if(!AuthorityPawn||!AuthorityPawn->HasAuthority())return false;
    }
    else if(bPersistenceBlocked||(GetWorld()&&GetWorld()->GetNetMode()==NM_DedicatedServer)){Message=TEXT("当前玩家数据不可写入");return false;}
    bool CurrencyChanged=false;FString CurrencyReason;
    if(!ColdSteelCurrency::Normalize(State,CurrencyChanged,CurrencyReason)){Message=CurrencyReason;return false;}
    RemoveRetiredItems(State);
    RefreshWeaponTuning(State,Definitions);
    RefreshBeltTuning(State,Definitions);
    bool AmmoChanged=false;
    if(!NormalizeAmmo(State,AmmoChanged)){Message=TEXT("弹药数据迁移失败，原存档保留");return false;}
    NormalizeProductionState(State);
    NormalizeStaffState(State);
    if(!GetWorld()||GetWorld()->GetNetMode()!=NM_Client)
        ColdSteelFood::RebaseProfile(State,ColdSteelFood::Clock(this));
    ColdSteelItemRarity::Normalize(State.Items);
    // Equipment normally has highest priority. Thunder recall/catch reserves
    // the hands until its receipt; reject before saving or interrupting poses.
    ColdSteelSkills::Migrate(State);
    ColdSteelSkillTree::Migrate(State);
    ColdSteelQuickBar::Migrate(State);
    ColdSteelQuickBar::MirrorLegacy(State);
    NormalizeStamina(State);
    State.Survival.Normalize();
    // Original updateMaxStats preserves the missing HP/MP amount when maxima grow.
    if(State.Health>0)State.Health=FMath::Clamp(double(State.Health)+ResourceMaximum(State,false)-ResourceMaximum(Current,false),0.,ResourceMaximum(State,false));
    State.Mana=FMath::Clamp(double(State.Mana)+ResourceMaximum(State,true)-ResourceMaximum(Current,true),0.,ResourceMaximum(State,true));
    if(!ColdSteelWarehouse::MigrateLayout(State)){Message=TEXT("仓库布局迁移失败，原存档保留");return false;}
    FString Reason;if(!Validate(State,Reason)){Message=Reason;return false;}
    auto* Tool=RuntimePawn()?RuntimePawn()->FindComponentByClass<UProductionToolComponent>():nullptr;
    if(Tool&&!Tool->ValidateThunderEquipmentChange(Current,State,Message))return false;
    if(bStagingNetworkContainer){Publish(State);return true;}
    if(bAudit&&AuditFailNextSave){AuditFailNextSave=false;Message=TEXT("验收注入：保存失败，操作未提交");return false;}
    State.Version=2;
    State.Generation=Current.Generation+1;
    if(bNetShadowProfile)
    {
        const bool SendSmithLesson=State.BlacksmithApprenticeshipStage!=Current.BlacksmithApprenticeshipStage;
        const bool SendCarpenterLesson=State.CarpenterApprenticeshipStage!=Current.CarpenterApprenticeshipStage;
        if(!CampfireGuestSaveSlot.IsEmpty())
        {
            auto* Saved=NewObject<UColdSteelProfileSave>();Saved->Profile=State;StripNetworkContainerView(Saved->Profile);
            if(!UGameplayStatics::SaveGameToSlot(Saved,CampfireGuestSaveSlot,0))
            {bTransactionSaveUnconfirmed|=bSavingTransaction;Message=TEXT("客机交易写入未确认，已保留原存档等待恢复");return false;}
        }
        Publish(State);
        if(!CampfireGuestSaveSlot.IsEmpty()&&(SendSmithLesson||SendCarpenterLesson))
        {
            auto* Pawn=RuntimePawn();
            auto* Owner=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
            if(Owner&&Owner->GetShadowModel()==this)
            {
                if(SendSmithLesson)Owner->ClientBlacksmithLesson(Current.NetworkProfileId,Current.BlacksmithApprenticeshipStage);
                if(SendCarpenterLesson)Owner->ClientCarpenterLesson(Current.NetworkProfileId,Current.CarpenterApprenticeshipStage);
            }
        }
        if(Tool)Tool->CommitThunderEquipmentChange(Current);
        if(bApplyPawn)ApplyToPawn();
        OnChanged.Broadcast();return true;
    }
    auto* Save=Cast<UColdSteelProfileSave>(UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));Save->Profile=State;
    StripNetworkContainerView(Save->Profile);
    const FString Slot=SaveSlot+(State.Generation%2?TEXT("_A"):TEXT("_B"));
    if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0)){bTransactionSaveUnconfirmed|=bSavingTransaction;Message=TEXT("保存失败，操作未提交");return false;}
    TArray<uint8> Written;
    if(!UGameplayStatics::LoadDataFromSlot(Written,Slot,0)||!FFileHelper::SaveStringToFile(HashBytes(Written),*ChecksumPath(Slot))){bTransactionSaveUnconfirmed|=bSavingTransaction;Message=TEXT("完整性记录写入失败，操作未提交");return false;}
    auto* Verify=ReadCheckedProfile(Slot);
    if(!Verify||Verify->Profile.Generation!=State.Generation||!Validate(Verify->Profile,Reason)){bTransactionSaveUnconfirmed|=bSavingTransaction;Message=TEXT("存档写入校验失败，操作未提交");return false;}
    QueueProgressNotices(Current,State);
    QueueAcquisitionNotices(Current,State);
    Publish(State);Message=TEXT("已保存");
    if(Tool)Tool->CommitThunderEquipmentChange(Current);
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
    const int64 GainedExperience=GainedCharacterExperience(State);
    const FGuid LeveledHorse=CreditPresentMountExperience(State,GainedExperience);
    bool bLeveled=false;
    for(const auto& Pair:State.Skills)
    {
        const auto* Before=Current.Skills.Find(Pair.Key);
        if(!Before||Pair.Value.Level>Before->Level){bLeveled=true;break;}
    }
    bLeveled|=State.Level>Current.Level;
    // A level-up owns a progress notice plus derived stat changes, so it keeps
    // the immediate checked transaction. Keep Current as the before-state and
    // persist the reward directly: Snapshot() still carries the old public Level
    // and AttributePoints until Publish(), and would discard the earned level.
    if(bLeveled)
    {
        if(PersistState(State,true)){ApplyCommittedMountLevel(LeveledHorse);QueueExperienceNotice(GainedExperience);return true;}
        // The reward is still accepted in memory when disk persistence fails.
        // Publish the public mirrors as well, so a later snapshot cannot roll it
        // back; callers must also mark these kills rewarded to prevent duplicates.
        NormalizeStamina(State);
        if(State.Health>0)State.Health=FMath::Clamp(double(State.Health)+ResourceMaximum(State,false)-ResourceMaximum(Current,false),0.,ResourceMaximum(State,false));
        State.Mana=FMath::Clamp(double(State.Mana)+ResourceMaximum(State,true)-ResourceMaximum(Current,true),0.,ResourceMaximum(State,true));
        QueueProgressNotices(Current,State);
        QueueAcquisitionNotices(Current,State);
        Publish(State);
        ApplyCommittedMountLevel(LeveledHorse);
        bTrainingDirty=true;TrainingFlushAccumulator=0.f;
        QueueExperienceNotice(GainedExperience);
        ApplyToPawn();OnChanged.Broadcast();return true;
    }
    Current=MoveTemp(State);
    ApplyCommittedMountLevel(LeveledHorse);
    QueueExperienceNotice(GainedExperience);
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    // Coalesced panel refresh: readings already come from the live profile, so
    // the sheet does not need to rebuild once per bullet.
    const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0.;
    if(Now-LastTrainingPublish>=.15){LastTrainingPublish=Now;OnChanged.Broadcast();}
    return true;
}
