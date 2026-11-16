#include "UnknownHumanoid.h"
#include "MonsterDamageBalance.h"
#include "../Weapons/Kukri/KukriSweepClock.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "MonsterCoreStats.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatItemFormula.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/FullAutoTrigger.h"
#include "../Weapons/Saiga12KWeaponAssets.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Production/ProductionToolStats.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/Super90Spread.h"
#include "Engine/GameInstance.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameModeBase.h"

namespace UnknownLoadouts
{
    // The items in each row occupy the five slots checked by the player's set bonuses.
    constexpr int32 Slots[] = {1, 3, 7, 13, 15};
    constexpr const TCHAR* Sets[][5] = {
        {TEXT("ue_steel_armet"), TEXT("ue_steel_gauntlets"), TEXT("ue_chainmail_shirt"), TEXT("ue_armored_boots"), TEXT("ue_chainmail_pants")},
        {TEXT("ue_st6_tactical_helmet"), TEXT("ue_hardknuckle_gloves"), TEXT("ue_st6_sleeves"), TEXT("ue_st6_tactical_boots"), TEXT("ue_st6_tactical_pants")},
        {TEXT("ue_blue_mage_hat"), TEXT("ue_blue_mage_gloves"), TEXT("ue_blue_mage_robe"), TEXT("ue_blue_mage_boots"), TEXT("ue_blue_mage_pants")},
        {TEXT("ue_ranger_feather_hat"), TEXT("ue_field_gloves"), TEXT("ue_field_sweater"), TEXT("ue_leather_boots"), TEXT("ue_leather_pants")},
        {TEXT("ue_field_hat"), TEXT("ue_original_gloves"), TEXT("ue_work_jacket"), TEXT("ue_boots"), TEXT("ue_cargo_pants")}
    };

    // These catalogs are immutable after the game instance initializes. Keep IDs only.
    struct FWeaponPools
    {
        TWeakObjectPtr<UColdSteelStatusModel> Catalog;
        TArray<FString> ByRole[4];
        void Read(UColdSteelStatusModel& Source, const UGunsmithSystem& Guns)
        {
            if (Catalog.Get() == &Source) return;
            Catalog = &Source;
            for (auto& Pool : ByRole) Pool.Reset();
            for (const auto& Pair : Source.ItemDefinitions())
            {
                FColdSteelItem Item;
                Item.Definition = Pair.Key;
                Item.Data = Pair.Value;
                if (ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("bow")) ByRole[3].Add(Pair.Key);
                else if (Guns.Weapon(Pair.Key)) ByRole[1].Add(Pair.Key);
                else if (ColdSteelInventory::Text(Item,TEXT("weaponType")) == TEXT("staff")
                    && !ColdSteelInventory::Flag(Item,TEXT("isTwoHanded"))) ByRole[2].Add(Pair.Key);
                else if ((ColdSteelInventory::IsTwoHandedSword(Item) || ColdSteelInventory::IsTwoHandedBlunt(Item) || ColdSteelInventory::IsOneHandedBlade(Item))
                    && !ColdSteelInventory::Text(Item,TEXT("world_mesh")).IsEmpty()
                    && ColdSteelInventory::CanEquip(Item,6)) ByRole[0].Add(Pair.Key);
            }
        }
    };

    void Allocate(FColdSteelProfile& Profile, const FColdSteelItem& Weapon, const FColdSteelItem* Offhand, EUnknownRole Role, const UColdSteelEnhancementSystem& Rules)
    {
        const TArray<FName> Keys = {TEXT("str"),TEXT("dex"),TEXT("intt"),TEXT("con"),TEXT("wis"),TEXT("luck")};
        for (FName Key : Keys) Profile.Attributes.Add(Key,10);
        TMap<FName,double> Weights;
        if (Role == EUnknownRole::Magic)
        {
            Weights.Add(TEXT("intt"),1.5);
            Weights.Add(TEXT("wis"),.5);
            for (const FColdSteelItem* Implement : {&Weapon,Offhand})
            {
                if (!Implement) continue;
                const auto Data=CombatItemFormula::ReadOnly(*Implement);
                const TSharedPtr<FJsonObject>* Formula=nullptr;
                if (!Data || !Data->TryGetObjectField(TEXT("matkFormula"),Formula)) continue;
                double Int=0, Wis=0;
                (*Formula)->TryGetNumberField(TEXT("intMul"),Int);
                (*Formula)->TryGetNumberField(TEXT("wisMul"),Wis);
                Weights[TEXT("intt")]+=Int;
                Weights[TEXT("wis")]+=Wis;
            }
        }
        else if (const auto Formula = Rules.AttackFormula(Weapon))
        {
            const TArray<TSharedPtr<FJsonValue>>* Terms = nullptr;
            if (Formula->TryGetArrayField(TEXT("attrs"),Terms))
                for (const auto& Term : *Terms)
                {
                    const auto Row = Term->AsObject();
                    if (!Row) continue;
                    const FString Name = Row->GetStringField(TEXT("key"));
                    const FName Key(Name == TEXT("int") ? TEXT("intt") : *Name);
                    if (Profile.Attributes.Contains(Key))
                        Weights.FindOrAdd(Key) += FMath::Max(0.,Row->GetNumberField(TEXT("base")));
                }
        }
        double Sum = 0;
        for (const auto& Pair : Weights) Sum += Pair.Value;
        if (Sum > 0) for (auto& Pair : Weights) Pair.Value *= .8 / Sum;
        Weights.FindOrAdd(TEXT("con")) += .15;
        Weights.FindOrAdd(TEXT("dex")) += .05;
        // Largest cumulative deficit gives reproducible integer allocations with no lost points.
        TMap<FName,double> Credit;
        for (int32 Point=0; Point<3*(Profile.Level-1); ++Point)
        {
            FName Best = Keys[0];
            for (FName Key : Keys) Credit.FindOrAdd(Key) += Weights.FindRef(Key);
            for (FName Key : Keys) if (Credit[Key] > Credit[Best]) Best = Key;
            ++Profile.Attributes[Best];
            Credit[Best] -= Sum > 0 ? 1. : .2;
        }
    }
}

UColdSteelStatusModel* AUnknownHumanoid::EquipmentModel() const { return Sheet.Get(); }

bool AUnknownHumanoid::Configure(EUnknownRole InRole, int32 Level)
{
    if (!HasAuthority() || !GetGameInstance() || Sheet) return false;
    auto* Catalog = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* Guns = GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto* Rules = GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
    if (!Catalog || !Guns || !Rules) return false;
    static UnknownLoadouts::FWeaponPools Pools;
    Pools.Read(*Catalog,*Guns);
    const auto& Pool = Pools.ByRole[static_cast<int32>(InRole)];
    if (Pool.IsEmpty()) return false;
    const FName Body=FMath::RandBool()?TEXT("jason"):TEXT("kaitlin");
    return EquipLoadout(*Catalog,*Rules,InRole,Level,Body,Pool[FMath::RandHelper(Pool.Num())]);
}

bool AUnknownHumanoid::EquipLoadout(UColdSteelStatusModel& Catalog,const UColdSteelEnhancementSystem& Rules,
    EUnknownRole InRole,int32 Level,FName Body,const FString& WeaponId)
{
    FColdSteelProfile Profile;
    Profile.Name = TEXT("未知");
    Profile.Level = Level;
    Profile.Hotbar.SetNum(4);
    Profile.HotbarDefinitions.SetNum(4);
    Profile.WarehouseLayoutVersion = 1;
    Loadout.Role = InRole;
    Loadout.Level = Level;
    Loadout.Body = Body;
    Profile.PlayerHeadId = Loadout.Body;
    Loadout.Weapon = WeaponId;
    auto Weapon = Catalog.CreateItem(Loadout.Weapon);
    Weapon.Place = 1;
    Weapon.Cell = Profile.ActiveWeaponSlot;
    FColdSteelItem Book;
    if (InRole==EUnknownRole::Magic)
    {
        Book=Catalog.CreateItem(TEXT("ue_alchemy_spellbook"));
        Book.Place=1;
        Book.Cell=Profile.ActiveWeaponSlot==6?8:11;
        if (Book.Data.IsEmpty() || !ColdSteelInventory::CanEquip(Book,Book.Cell)) return false;
        Loadout.Offhand=Book.Definition;
    }
    UnknownLoadouts::Allocate(Profile,Weapon,InRole==EUnknownRole::Magic?&Book:nullptr,InRole,Rules);
    Profile.Items.Add(MoveTemp(Weapon));
    if (InRole==EUnknownRole::Magic) Profile.Items.Add(MoveTemp(Book));
    // Class identity also determines the real five-piece set bonus.
    const int32 GunSets[]={1,3,4};
    const int32 SetIndex=InRole==EUnknownRole::Melee?0:InRole==EUnknownRole::Magic?2:
        InRole==EUnknownRole::Bow?3:GunSets[FMath::RandHelper(UE_ARRAY_COUNT(GunSets))];
    const auto& Outfit = UnknownLoadouts::Sets[SetIndex];
    for (int32 I=0; I<UE_ARRAY_COUNT(Outfit); ++I)
    {
        auto Piece = Catalog.CreateItem(Outfit[I]);
        if (Piece.Data.IsEmpty()) return false;
        Piece.Place = 1;
        Piece.Cell = UnknownLoadouts::Slots[I];
        auto& Slot = Loadout.Outfit.AddDefaulted_GetRef();
        Slot.Slot = Piece.Cell;
        Slot.Definition = FName(*Piece.Definition);
        Profile.Items.Add(MoveTemp(Piece));
    }
    ColdSteelSkills::Migrate(Profile);
    if (InRole==EUnknownRole::Bow)
    {
        Loadout.BackupBlade=TEXT("ue_kukri");
        for (int32 Slot:{9,11})
        {
            auto Blade=Catalog.CreateItem(Loadout.BackupBlade);
            if (Blade.Data.IsEmpty() || !ColdSteelInventory::CanEquip(Blade,Slot)) return false;
            Blade.Place=1; Blade.Cell=Slot; Profile.Items.Add(MoveTemp(Blade));
        }
        for (const FName Skill:{FName(TEXT("bowMastery")),FName(TEXT("heartPiercingArrow")),FName(TEXT("elementalArrow")),
            FName(TEXT("magicArrowRain")),FName(TEXT("illuminationArrow")),FName(TEXT("fireball")),FName(TEXT("iceSpike")),FName(TEXT("lightningStrike"))})
            Profile.Skills.FindOrAdd(Skill).Level=FMath::Clamp(Level/10,1,3);
        Profile.ActiveWeaponSlot=6;
        BowSheet=Catalog.CreateEquipmentModel(Profile);
        Profile.ActiveWeaponSlot=9;
        BladeSheet=Catalog.CreateEquipmentModel(Profile);
        Profile.ActiveWeaponSlot=6;
    }
    Sheet = InRole==EUnknownRole::Bow?BowSheet.Get():Catalog.CreateEquipmentModel(Profile);
    if (!Sheet || !Sheet->Equipped()) return false;
    CacheStats();
    return true;
}

void AUnknownHumanoid::CacheStats()
{
    const auto& Weapon = *Sheet->Equipped();
    WeaponType = FName(*ColdSteelInventory::Text(Weapon,TEXT("weaponType")));
    MaxHealth = Health = Sheet->Derived(TEXT("maxHp"));
    MaxStamina = Stamina = Sheet->MaxStamina();
    HealthRegen = Sheet->Derived(TEXT("hpRegen"));
    Defense = Sheet->Derived(TEXT("def"));
    MagicDefense = Sheet->Derived(TEXT("mdef"));
    CritResistance = Sheet->Derived(TEXT("critRes"));
    AttributeWeight = .08*(Sheet->Attribute(TEXT("str"))+Sheet->Attribute(TEXT("dex"))+Sheet->Attribute(TEXT("intt"))+Sheet->Attribute(TEXT("wis")))
        + .1*Sheet->Attribute(TEXT("con")) + .04*Sheet->Attribute(TEXT("luck"));
    CriticalChance = Sheet->Derived(TEXT("crit"));
    CriticalBonus = Sheet->CriticalStrikeEffect().CriticalDamageBonus + ColdSteelInventory::Number(Weapon,TEXT("critDamageBonus"));
    WeakpointPercent = ColdSteelInventory::Number(Weapon,TEXT("innate_weakpoint_percent"));
    const auto* Player = GetDefault<AFPSGAMECharacter>();
    if (const auto* Mode=GetWorld()->GetAuthGameMode(); Mode && Mode->DefaultPawnClass && Mode->DefaultPawnClass->IsChildOf(AFPSGAMECharacter::StaticClass()))
        Player=Mode->DefaultPawnClass->GetDefaultObject<AFPSGAMECharacter>();
    if (const auto* Rules=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
    {
        CriticalChance+=100.f*Rules->Effect(Weapon,TEXT("critRate"));
        PhysicalPenetration=ColdSteelInventory::Number(Weapon,TEXT("innate_armor_penetration"))+Rules->CraftEffect(Weapon,TEXT("armorPenetrationPercent"))+Rules->Effect(Weapon,TEXT("armorPenetrationPercent"));
        MagicPenetration=Rules->CraftEffect(Weapon,TEXT("magicPenetrationPercent"))+Rules->Effect(Weapon,TEXT("magicPenetrationPercent"));
    }
    const auto* Movement = Player->GetCharacterMovement();
    auto* Move = GetCharacterMovement();
    Move->MaxAcceleration = Movement->MaxAcceleration;
    Move->BrakingDecelerationWalking = Movement->BrakingDecelerationWalking;
    Move->GroundFriction = Movement->GroundFriction;
    Move->JumpZVelocity = Movement->JumpZVelocity;
    float Speed = Sheet->CombatMoveMultiplier();
    if (Loadout.Role == EUnknownRole::Gun) Speed *= Sheet->PistolMovementMultiplier()*Sheet->MachineGunMovementMultiplier();
    WalkSpeed = Player->WalkSpeed*Speed;
    RunSpeed = Player->SprintSpeed*Speed;
    AimWalkSpeed = Player->ADSWalkSpeed*Speed;
    Move->MaxWalkSpeed = WalkSpeed;
    RecoveryRate = Sheet->StaminaRecoveryRate();
    SprintDrain = Sheet->SprintStaminaPerSecond();

    switch (bBowBlades?EUnknownRole::Melee:Loadout.Role)
    {
    case EUnknownRole::Melee:
    {
        const auto Stats = ColdSteelMelee::Evaluate(Weapon,Sheet);
        WeaponDamage = Stats.DamageParts;
        AttackSeconds = Stats.AttackSeconds;
        AttackRange = Stats.SlashReach;
        StaminaCost = Stats.AttackStamina;
        MeleeContactFraction = RuneSwordRhythm::ContactStart/RuneSwordRhythm::AttackEnd;
        MeleeSecondContact = 0.f;
        if (ColdSteelInventory::UsesKukriMoveset(Weapon))
        {
            const auto& Clock=KukriAttackTiming::FSweepClock::Get(bBowBlades);
            const float Rate=KukriAttackTiming::PlayRate(Stats.AttackRate);
            AttackSeconds=Clock.Duration(Rate);
            MeleeContactFraction=Clock.ContactSeconds(0,Rate)/AttackSeconds;
            if (bBowBlades) MeleeSecondContact=Clock.ContactSeconds(1,Rate);
        }
        if (ColdSteelInventory::IsTwoHandedBlunt(Weapon))
        {
            // Players execute hammers through ProductionTool, not the sword
            // clock/reach. Keep damage, stamina and visual contact on that clock.
            const auto Hammer = ColdSteelTool::Evaluate(Weapon,Sheet);
            WeaponDamage = Hammer.Damage;
            AttackSeconds = Hammer.SwingSeconds;
            AttackRange = Hammer.CombatReachCM;
            StaminaCost = Hammer.StaminaCost;
            MeleeContactFraction = Hammer.ContactSeconds/FMath::Max(.001,Hammer.SwingSeconds);
        }
        PreferredRange = FMath::Min(145.f,AttackRange*.65f);
        if (bBowBlades) StaminaCost=ColdSteelMelee::ComboAttackStamina(&Weapon,Sheet,true);
        PhysicalPenetration += Stats.Modifiers.PhysicalArmorPenetration;
        CriticalChance += Stats.Modifiers.MeleeCriticalChanceAdd;
        CriticalBonus += Stats.Modifiers.MeleeCriticalDamageBonus;
        break;
    }
    case EUnknownRole::Gun:
    {
        const auto* Guns = GetGameInstance()->GetSubsystem<UGunsmithSystem>();
        const auto Parts = Guns->Installed(Weapon);
        const auto Stats = Guns->CalculateItem(Weapon,Parts);
        WeaponDamage = ColdSteelWeaponStats::DamageParts(Weapon,Sheet,Stats.Damage).Scaled(Sheet->AmmoDamageMultiplier(Weapon));
        PhysicalPenetration += Sheet->AmmoArmorPenetration(Weapon);
        BurstRecovery = Stats.BurstDelay;
        CriticalBonus += Stats.FirearmCriticalDamageBonus;
        AttackSeconds = ColdSteelWeaponStats::Interval(&Weapon,Sheet,Stats.Interval);
        ReloadSeconds = ColdSteelWeaponStats::Reload(&Weapon,Sheet,Stats.EmptyReload);
        TacticalReloadSeconds = ColdSteelWeaponStats::Reload(&Weapon,Sheet,Stats.Reload);
        AimSeconds = FMath::Max(.08f,float(Stats.ADS*Sheet->ADSTimeMultiplier()));
        Capacity = FMath::Max(1,Stats.Capacity);
        Magazine = FMath::Clamp(Weapon.Magazine,0,Capacity);
        const bool Automatic=WeaponType==TEXT("rifle") || WeaponType==TEXT("machineGun")
            || Weapon.Definition==Saiga12KWeaponAssets::Definition
            || FullAutoTrigger::Automatic(Weapon,FullAutoTrigger::Installed(Weapon.Definition,Parts));
        ShotAccuracyPercent=(Automatic || Stats.BurstCount>1) ? 20 : 33;
        BurstSize = Stats.BurstCount>1 ? Stats.BurstCount :
            WeaponType==TEXT("machineGun") ? 6 : WeaponType==TEXT("rifle") ? 3 : 1;
        EffectiveRange = Stats.Range*100.f*Sheet->AmmoRangeMultiplier(Weapon);
        BulletSpeed = Stats.Speed*100.f;
        Pellets = Sheet->AmmoProjectileCount(Weapon,WeaponType==TEXT("shotgun")?Super90WeaponAssets::PelletCount:1);
        PelletCone = Super90Spread::ConeRadians(Pellets,true,Guns->PelletSpreadMultiplier(Weapon.Definition,Parts));
        AttackRange = FMath::Min(EffectiveRange,WeaponType==TEXT("shotgun")?950.f:WeaponType==TEXT("pistol")?1600.f:3400.f);
        PreferredRange = AttackRange*(WeaponType==TEXT("sniper")?.84f:.7f);
        break;
    }
    case EUnknownRole::Magic:
        Spell = Sheet->FireballStats(1);
        AttackRange = Spell.Range*.9f;
        PreferredRange = AttackRange*.72f;
        AttackSeconds = 1.f/FMath::Max(.1f,Spell.CastSpeed);
        break;
    case EUnknownRole::Bow:
        CacheBowStats();
        break;
    }
    // Convert only the monster's outgoing snapshot. The equipment model remains
    // the real player model for movement, health, defenses and item identity.
    if(Loadout.Role!=EUnknownRole::Magic)
    {
        const float Raw=WeaponDamage.Total();
        const float Balanced=UnknownDamageBalance::Weapon(Raw,WeaponType,Loadout.Role==EUnknownRole::Gun,
            ShotAccuracyPercent==20,Loadout.Level,AttackSeconds,bBowBlades?2:1);
        if(Raw>0.f)WeaponDamage=WeaponDamage.Scaled(Balanced/Raw);
        CriticalBonus=FMath::Clamp(CriticalBonus,0.f,.25f);
        WeakpointPercent=FMath::Clamp(WeakpointPercent,0.f,10.f);
        PhysicalPenetration=FMath::Clamp(PhysicalPenetration,0.f,.2f);
        MagicPenetration=FMath::Clamp(MagicPenetration,0.f,.15f);
    }
}

void AUnknownHumanoid::CoreStats(FMonsterCoreStats& Out) const
{
    Out.Def = Defense;
    Out.Mdef = MagicDefense;
    if (auto* Armor=FindComponentByClass<UFPSIceArmorComponent>())
    { Out.Def+=Armor->DefenseBonus(false); Out.Mdef+=Armor->DefenseBonus(true); }
    Out.CritRes = CritResistance;
    Out.AttrWeight = AttributeWeight;
    Out.Level = Loadout.Level;
    Out.Rank = EMonsterRank::Normal;
    Out.ToughnessClass = Loadout.Role==EUnknownRole::Magic ? EMonsterToughnessClass::Caster : EMonsterToughnessClass::Light;
}
