#include "MonsterDamageAuditCommandlet.h"
#include "DevelopmentSpawnComponent.h"
#include "../Monsters/UnknownHumanoid.h"
#include "../Monsters/MonsterDamageBalance.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Production/ProductionToolStats.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Skills/HeartPiercingArrowTypes.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

namespace
{
    TSharedRef<FJsonObject> Row(const FString& Weapon,int32 Level,const FString& Attack,float Before,float After,
        float OldCrit=0.f,float NewCrit=0.f,float Count=1.f)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("weapon"),Weapon);R->SetNumberField(TEXT("level"),Level);
        R->SetStringField(TEXT("attack"),Attack);R->SetNumberField(TEXT("raw_before"),Before);R->SetNumberField(TEXT("raw_after"),After);
        R->SetNumberField(TEXT("hits_or_ticks"),Count);R->SetNumberField(TEXT("all_hits_before"),Before*Count);
        R->SetNumberField(TEXT("all_hits_after"),After*Count);
        R->SetNumberField(TEXT("critical_before"),Before*(1+OldCrit));R->SetNumberField(TEXT("critical_after"),After*(1+NewCrit));
        return R;
    }
}
int32 UMonsterDamageAuditCommandlet::Main(const FString& Params)
{
    const FString Profile=TEXT("MonsterDamageAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    const FString Original=FCommandLine::Get();FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("MonsterDamageAuditWorld"));
    FCommandLine::Set(*Original);auto* World=GI->GetWorld();
    ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();};
    auto* Catalog=GI->GetSubsystem<UColdSteelStatusModel>();auto* Guns=GI->GetSubsystem<UGunsmithSystem>();
    auto* Rules=GI->GetSubsystem<UColdSteelEnhancementSystem>();
    if(!World||!Catalog||!Guns||!Rules||!Catalog->IsAudit()||Catalog->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    TArray<FString> Ids;Catalog->ItemDefinitions().GetKeys(Ids);Ids.Sort();
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Weapons=0,Failures=0;
    auto Add=[&](TSharedRef<FJsonObject> R){Rows.Add(MakeShared<FJsonValueObject>(R));};
    for(const auto& Id:Ids)
    {
        FColdSteelItem Item;Item.Definition=Id;Item.Data=Catalog->ItemDefinitions().FindChecked(Id);
        const FString Type=ColdSteelInventory::Text(Item,TEXT("weaponType"));EUnknownRole Role;
        if(Type==TEXT("bow"))Role=EUnknownRole::Bow;
        else if(Guns->Weapon(Id))Role=EUnknownRole::Gun;
        else if(Type==TEXT("staff")&&!ColdSteelInventory::Flag(Item,TEXT("isTwoHanded")))Role=EUnknownRole::Magic;
        else if((ColdSteelInventory::IsTwoHandedSword(Item)||ColdSteelInventory::IsTwoHandedBlunt(Item)||ColdSteelInventory::IsOneHandedBlade(Item))&&
            !ColdSteelInventory::Text(Item,TEXT("world_mesh")).IsEmpty()&&ColdSteelInventory::CanEquip(Item,6))Role=EUnknownRole::Melee;
        else continue;
        ++Weapons;
        for(int32 Level:{10,20,30})for(int32 Outfit=0;Outfit<(Role==EUnknownRole::Gun?3:1);++Outfit)
        {
            FActorSpawnParameters Spawn;Spawn.ObjectFlags=RF_Transient;
            Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* N=World->SpawnActor<AUnknownHumanoid>(Spawn);
            if(!N||!N->EquipLoadout(*Catalog,*Rules,Role,Level,TEXT("jason"),Id)){++Failures;if(N)N->Destroy();continue;}
            if(Role==EUnknownRole::Gun)
            {
                const int32 Slots[]={1,3,7,13,15};
                const TCHAR* Sets[][5]={
                    {TEXT("ue_st6_tactical_helmet"),TEXT("ue_hardknuckle_gloves"),TEXT("ue_st6_sleeves"),TEXT("ue_st6_tactical_boots"),TEXT("ue_st6_tactical_pants")},
                    {TEXT("ue_ranger_feather_hat"),TEXT("ue_field_gloves"),TEXT("ue_field_sweater"),TEXT("ue_leather_boots"),TEXT("ue_leather_pants")},
                    {TEXT("ue_field_hat"),TEXT("ue_original_gloves"),TEXT("ue_work_jacket"),TEXT("ue_boots"),TEXT("ue_cargo_pants")}};
                auto State=N->Sheet->Snapshot();
                for(auto& Piece:State.Items)if(Piece.Place==1)for(int32 I=0;I<5;++I)if(Piece.Cell==Slots[I])
                {Piece=Catalog->CreateItem(Sets[Outfit][I]);Piece.Place=1;Piece.Cell=Slots[I];break;}
                N->Sheet=Catalog->CreateEquipmentModel(State);N->CacheStats();
            }
            auto* M=N->Sheet.Get();const auto& W=*M->Equipped();const int32 Rank=Level/10;
            auto Magic=[&](const FString& Name,auto Before,auto After,float Count=1.f)
            {Add(Row(Id,Level,Name,Before.Damage*(1+Before.MagicDamageBonus),After.Damage*(1+After.MagicDamageBonus),Before.CriticalDamageBonus,After.CriticalDamageBonus,Count));};
            auto Spell=[&](const FString& Name,auto C,float Count=1.f){auto Before=C;UnknownDamageBalance::Tune(Level,C);Magic(Name,Before,C,Count);};
            if(Role!=EUnknownRole::Magic)
            {
                float Raw=0,OldCrit=M->CriticalStrikeEffect().CriticalDamageBonus+ColdSteelInventory::Number(W,TEXT("critDamageBonus"));
                if(Role==EUnknownRole::Gun){const auto S=Guns->CalculateItem(W,Guns->Installed(W));Raw=ColdSteelWeaponStats::DamageParts(W,M,S.Damage).Total()*M->AmmoDamageMultiplier(W);OldCrit+=S.FirearmCriticalDamageBonus;}
                else if(Role==EUnknownRole::Bow){const auto S=ColdSteelBow::Evaluate(W,M);Raw=S.Damage.Total()*M->AmmoDamageMultiplier(W);OldCrit=M->CriticalStrikeEffect().CriticalDamageBonus+S.CriticalDamageBonus;}
                else {const auto S=ColdSteelMelee::Evaluate(W,M);Raw=ColdSteelInventory::IsTwoHandedBlunt(W)?ColdSteelTool::Evaluate(W,M).Damage.Total():S.DamageParts.Total();OldCrit+=S.Modifiers.MeleeCriticalDamageBonus;}
                auto R=Row(Id,Level,TEXT("weapon"),Raw,N->WeaponDamage.Total(),OldCrit,N->CriticalBonus);
                R->SetStringField(TEXT("type"),Type);R->SetNumberField(TEXT("interval"),N->AttackSeconds);
                R->SetNumberField(TEXT("outfit_variant"),Outfit);
                R->SetNumberField(TEXT("pellets"),N->Pellets);R->SetNumberField(TEXT("weakpoint_after"),N->WeakpointPercent);
                R->SetNumberField(TEXT("accuracy_percent"),N->ShotAccuracyPercent);Add(R);
                if(Role==EUnknownRole::Bow)
                {
                    const auto P=HeartPiercingArrow::ForModel(M,Rank,ColdSteelBow::Evaluate(W,M).Draw);
                    Add(Row(Id,Level,TEXT("piercing"),Raw*P.DamageMultiplier,UnknownDamageBalance::Piercing(N->WeaponDamage.Total()*P.DamageMultiplier,Level),OldCrit,N->CriticalBonus));
                    for(auto E:{EArrowElement::Fire,EArrowElement::Ice,EArrowElement::Lightning})
                    {auto C=M->ElementalArrowStats(E,Rank),Before=C;UnknownDamageBalance::Tune(Level,C);
                        if(E==EArrowElement::Fire)Magic(TEXT("element_fire_extra"),Before.Fire,C.Fire);
                        else if(E==EArrowElement::Ice)Magic(TEXT("element_ice_extra"),Before.Ice,C.Ice);
                        else Magic(TEXT("element_lightning_extra"),Before.Lightning,C.Lightning);}
                    Spell(TEXT("magicArrowRain_one_volley"),M->MagicArrowRainStats(Rank));
                    auto Mark=M->IlluminationArrowStats(Rank);const float OldMark=Mark.DamageBonus;UnknownDamageBalance::Tune(Level,Mark);
                    Add(Row(Id,Level,TEXT("illumination_damage_bonus"),OldMark,Mark.DamageBonus));
                    N->bBowBlades=true;N->Sheet=N->BladeSheet;N->CacheStats();
                    const auto& Blade=*N->Sheet->Equipped();
                    const auto BladeStats=ColdSteelMelee::Evaluate(Blade,N->Sheet);
                    const float BladeCrit=N->Sheet->CriticalStrikeEffect().CriticalDamageBonus+ColdSteelInventory::Number(Blade,TEXT("critDamageBonus"))+BladeStats.Modifiers.MeleeCriticalDamageBonus;
                    Add(Row(Id,Level,TEXT("backup_dual_blades"),BladeStats.DamageParts.Total(),N->WeaponDamage.Total(),BladeCrit,N->CriticalBonus,2));
                }
            }
            else
            {
                Spell(TEXT("fireball"),M->FireballStats(Rank));
                const auto Spikes=M->IceSpikeStats(Rank);Spell(TEXT("iceSpike_volley"),Spikes,Spikes.Count);
                auto Wall=M->IceWallStats(Rank);const float OldWall=Wall.Damage;UnknownDamageBalance::Tune(Level,Wall);
                Add(Row(Id,Level,TEXT("iceWall"),OldWall,Wall.Damage));
                const auto Blizzard=M->BlizzardStats(Rank);Spell(TEXT("blizzard_tick"),Blizzard,FMath::CeilToFloat(Blizzard.Duration/Blizzard.TickSeconds));
                auto L=M->LightningStats(Rank),OldL=L;UnknownDamageBalance::Tune(Level,L);Magic(TEXT("lightning"),OldL,L);
                Add(Row(Id,Level,TEXT("lightning_overload"),OldL.OverloadDamage,L.OverloadDamage,OldL.CriticalDamageBonus,L.CriticalDamageBonus));
                Spell(TEXT("holyLight"),M->HolyLightStats(Rank));
                Add(Row(Id,Level,TEXT("lightningHaste_no_damage"),0,0));Add(Row(Id,Level,TEXT("iceArmor_no_damage"),0,0));
                for(FName Skill:{FName(TEXT("meteor")),FName(TEXT("flameArmor")),FName(TEXT("dragonBreath"))})
                {
                    auto C=M->FireMagicStats(Skill,Rank),Before=C;UnknownDamageBalance::Tune(Level,C);
                    Magic(Skill.ToString(),Before,C,Skill==TEXT("dragonBreath")?FMath::CeilToFloat(C.Duration/C.TickSeconds):1);
                    Add(Row(Id,Level,Skill.ToString()+TEXT("_aura_tick"),Before.AuraDamage*(1+Before.MagicDamageBonus),C.AuraDamage,Before.CriticalDamageBonus,C.CriticalDamageBonus,FMath::CeilToFloat(C.Duration/C.TickSeconds)));
                    Add(Row(Id,Level,Skill.ToString()+TEXT("_burn_per_stack_tick"),FMath::FloorToFloat(Before.MagicAttack*Before.BurnMultiplier),FMath::FloorToFloat(C.MagicAttack*C.BurnMultiplier)));
                }
                for(bool Lance:{false,true})
                {
                    const FName Skill=Lance?TEXT("thunderLance"):TEXT("stormDomain");
                    auto C=M->ElectricMagicStats(Skill,Rank),Before=C;UnknownDamageBalance::Tune(Level,C,Lance);
                    if(Lance){Before.Hit.Damage*=Before.ChargeBonus*(1+4*Before.StackDamage);C.Hit.Damage*=C.ChargeBonus*(1+4*C.StackDamage);}
                    Magic(Skill.ToString(),Before.Hit,C.Hit,Lance?1:FMath::CeilToFloat(C.Duration/C.StrikeSeconds));
                    Add(Row(Id,Level,Skill.ToString()+TEXT("_overload"),Before.Hit.OverloadDamage,C.Hit.OverloadDamage,Before.Hit.CriticalDamageBonus,C.Hit.CriticalDamageBonus));
                }
            }
            N->Destroy();
        }
    }
    // Read the actual F6 class defaults, including Blueprint overrides. No actor
    // from this roster is spawned, ticked or saved by this property inventory.
    TArray<TSharedPtr<FJsonValue>> Roster;
    for(const auto& Entry:GetDefault<UDevelopmentSpawnComponent>()->GetMonsters())
    {
        if(!Entry.WeaponGroup.IsNone())continue;
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("id"),Entry.Id.ToString());
        R->SetStringField(TEXT("name"),Entry.Name.ToString());R->SetStringField(TEXT("class"),Entry.CharacterClass.ToString());
        auto* Class=Entry.CharacterClass.LoadSynchronous();
        if(!Class){R->SetBoolField(TEXT("loaded"),false);++Failures;Roster.Add(MakeShared<FJsonValueObject>(R));continue;}
        R->SetBoolField(TEXT("loaded"),true);auto Values=MakeShared<FJsonObject>();
        auto Read=[&](const UObject* Object,const FString& Prefix)
        {for(TFieldIterator<FNumericProperty> It(Object->GetClass());It;++It)
            {const FString Key=It->GetName();if(Key.Contains(TEXT("Damage"))||Key.Contains(TEXT("Multiplier"))||Key==TEXT("PhysicalAttack")||Key==TEXT("MagicAttack"))
                {const void* Value=It->ContainerPtrToValuePtr<void>(Object);Values->SetNumberField(Prefix+Key,It->IsFloatingPoint()?It->GetFloatingPointPropertyValue(Value):double(It->GetSignedIntPropertyValue(Value)));}}};
        auto* Default=Class->GetDefaultObject<ACharacter>();Read(Default,TEXT(""));
        TInlineComponentArray<UActorComponent*> Components(Default);
        for(const auto* Component:Components)Read(Component,Component->GetName()+TEXT("."));
        R->SetObjectField(TEXT("numeric_properties"),Values);Roster.Add(MakeShared<FJsonValueObject>(R));
    }
    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("weapons"),Weapons);Root->SetNumberField(TEXT("failed_loadouts"),Failures);
    Root->SetArrayField(TEXT("f6_class_defaults"),Roster);
    Root->SetStringField(TEXT("scope"),TEXT("Live catalog/native equipment formulas, all three gun outfits and F6 Blueprint class-default properties. No BeginPlay, simulation, renderer, player-save edits or visual acceptance. Raw damage before defenses."));
    Root->SetArrayField(TEXT("rows"),Rows);FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    const FString Out=FPaths::ProjectSavedDir()/TEXT("Audits/MonsterDamageBalance20261115.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Out),true);
    const bool Saved=FFileHelper::SaveStringToFile(Json,*Out);
    UE_LOG(LogTemp,Display,TEXT("MONSTER_DAMAGE_AUDIT weapons=%d rows=%d failed_loadouts=%d saved=%d"),Weapons,Rows.Num(),Failures,Saved);
    return Saved&&Failures==0?0:2;
}
