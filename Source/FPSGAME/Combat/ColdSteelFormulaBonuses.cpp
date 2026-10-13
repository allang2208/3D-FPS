#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Building/WoodworkingQuality.h"
#include "../UI/StatusEffectsComponent.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "CoreCombatFormula.h"
#include "CombatItemFormula.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Weapons/Spellbook/SpellbookFocusMana.h"
#include "../Dungeons/DungeonRunSubsystem.h"
namespace
{
using J=TSharedPtr<const FJsonObject>;
J Read(const FColdSteelItem* I){return I?CombatItemFormula::ReadOnly(*I):nullptr;}
J Obj(J O,const TCHAR* K){const TSharedPtr<FJsonObject>* V=nullptr;return O&&O->TryGetObjectField(K,V)?*V:nullptr;}
double Num(J O,const TCHAR* K,double Default=0){double V=Default;if(O)O->TryGetNumberField(K,V);return V;}
double Now(){return FDateTime::UtcNow().ToUnixTimestamp();}
}
FString UColdSteelStatusModel::ArmorSet()const
{
    FString Set;
    for(int32 Slot:{1,7,13}){const auto* I=Equipped(Slot);if(!I)return {};FString Id;const auto Data=Read(I);if(Data)Data->TryGetStringField(TEXT("armorSet"),Id);if(Id.IsEmpty()||(!Set.IsEmpty()&&Id!=Set))return {};Set=Id;}
    return Set;
}
double UColdSteelStatusModel::SetEffect(FName Key)const
{
    const FString S=ArmorSet();
    if(Key==TEXT("speed"))
    {if(S==TEXT("light")||S==TEXT("holy"))return 1.10;if(S==TEXT("flowing"))return 1.15;if(S==TEXT("heavy"))return .85;if(S==TEXT("zhenyue")||S==TEXT("oracle"))return .88;if(S==TEXT("stellar"))return 1.08;if(S==TEXT("tiangang"))return .90;return 1;}
    if(Key==TEXT("cooldown")){if(S==TEXT("robe"))return .12;if(S==TEXT("eclipse"))return .18;if(S==TEXT("lunar"))return .22;if(S==TEXT("oracle_robe"))return .28;}
    if(Key==TEXT("magicDamage")){if(S==TEXT("robe"))return .18;if(S==TEXT("eclipse"))return .25;if(S==TEXT("lunar"))return .30;if(S==TEXT("oracle_robe"))return .35;}
    if(Key==TEXT("atk")){if(S==TEXT("stellar"))return .10;if(S==TEXT("holy"))return .15;}
    if(Key==TEXT("crit")){if(S==TEXT("stellar"))return 15;if(S==TEXT("holy"))return 20;}
    if(Key==TEXT("staminaRegen"))return S==TEXT("flowing")?1.12:1;
    return 0;
}
double UColdSteelStatusModel::TributeEffect(FName Key)const
{
    const bool Flat=Key.ToString().EndsWith(TEXT("Flat"));double Total=Flat?0:1;
    for(const auto& B:Current.FormulaBuffs)if(B.bTribute&&B.RemainingSeconds>0)if(const auto* V=B.Effects.Find(Key)){if(Flat)Total+=*V;else Total*=1+*V/100.;}
    return Total;
}
double UColdSteelStatusModel::TributeSpecial(FName Key)const
{
    double Best=0;
    for(const auto& B:Current.FormulaBuffs)if(B.bTribute&&B.RemainingSeconds>0)if(const auto* V=B.Specials.Find(Key))Best=FMath::Max(Best,double(*V));
    return Best;
}
bool UColdSteelStatusModel::ConsumePeachRevive(double& OutRatio)
{
    OutRatio=0;
    for(auto& B:Current.FormulaBuffs)
    {
        if(!B.bTribute||B.RemainingSeconds<=0||B.bPeachUsed)continue;
        const double V=B.Effects.FindRef(TEXT("revivePercent"));
        if(V>1){B.bPeachUsed=true;OutRatio=FMath::Clamp(V/100.,.01,.99);return true;} // 旧口径：revivePercent 为百分数（30→30%），缺省兜底由调用方处理
    }
    return false;
}
double UColdSteelStatusModel::TryActivateMoonshadow()
{
    const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0;
    if(Now<MoonshadowUntil)return MoonshadowUntil;
    for(auto& B:Current.FormulaBuffs)
    {
        if(!B.bTribute||B.RemainingSeconds<=0||B.bMoonshadowUsed)continue;
        const double Ms=B.Specials.FindRef(TEXT("moonshadowDuration"));
        if(Ms>0){B.bMoonshadowUsed=true;MoonshadowUntil=Now+Ms/1000.;return MoonshadowUntil;}
    }
    return 0;
}
bool UColdSteelStatusModel::IsMoonshadowActive()const
{
    const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0;
    return Now<MoonshadowUntil;
}
void UColdSteelStatusModel::SyncTributeTiles()
{
    // 旧 SPECIAL_BUFFS 键→卡片映射；effects 走聚合倍率>1，special 走原值>0。
    static const TPair<FName,FName> EffectTiles[]={ // {tribute effect key, tile type}
        {TEXT("expPercent"),TEXT("tributeSnowLotus")},{TEXT("killMpHealPercent"),TEXT("tributeGinseng")},{TEXT("revivePercent"),TEXT("tributePeach")}};
    static const TPair<FName,FName> SpecialTiles[]={ // {tribute special key, tile type}
        {TEXT("surviveCapPercent"),TEXT("tributeDiamond")},{TEXT("moonshadowDuration"),TEXT("tributeMoonstone")},
        {TEXT("oreUpgrade"),TEXT("tributePhilosopher")},{TEXT("friendlyLifestealPercent"),TEXT("tributeBloodVine")},
        {TEXT("friendlyAura"),TEXT("tributeWolfBanner")},{TEXT("recruitCountMul"),TEXT("tributeJadeTwins")},
        {TEXT("productionResourcePercent"),TEXT("tributeAstrolabe")}};
    TSet<FName> Active;
    for(const auto& P:EffectTiles)if(TributeEffect(P.Key)>1)Active.Add(P.Value);
    for(const auto& P:SpecialTiles)if(TributeSpecial(P.Key)>0)Active.Add(P.Value);
    auto* Pawn=CurrentPawn.Get();
    if(auto* Display=IsValid(Pawn)?UStatusEffectsComponent::GetOrCreate(Pawn):nullptr)
    {
        for(const auto& Old:PublishedTributeTiles)if(!Active.Contains(Old))Display->Remove(Old);
        for(const auto& Type:Active)if(!PublishedTributeTiles.Contains(Type))Display->SetPersistent(Type,TEXT("跟随献祭倒计时"));
    }
    PublishedTributeTiles=MoveTemp(Active);
}
double UColdSteelStatusModel::DungeonEffect(FName Key)const
{
    const auto* Run=UDungeonRunSubsystem::Get(GetWorld());
    double Total=Run?Run->ShrineEffect(Key):0.;
    for(const auto& B:Current.FormulaBuffs)if(!B.bTribute&&B.Battles>0)Total+=B.Effects.FindRef(Key);return Total;
}
double UColdSteelStatusModel::AdjustCombatStat(FName Key,double Value)const
{
    if(Key==TEXT("atk"))Value=std::floor(Value*(1+SetEffect(TEXT("atk"))));
    if(Key==TEXT("crit"))Value+=SetEffect(TEXT("crit"));
    const FName Percent(*(Key.ToString()+TEXT("Percent")));
    if(Key==TEXT("atk")||Key==TEXT("matk")||Key==TEXT("def")||Key==TEXT("mdef"))Value=std::floor(Value*(1+DungeonEffect(Percent)/100.));
    if(Key==TEXT("atk")||Key==TEXT("matk")||Key==TEXT("def")||Key==TEXT("mdef")||Key==TEXT("crit"))Value=std::floor(Value*TributeEffect(Percent));
    return Value;
}
double UColdSteelStatusModel::ItemMagicAttack(const FColdSteelItem& Item)const
{
    const FString Type=ColdSteelInventory::Text(Item,TEXT("weaponType"));
    if(Type!=TEXT("staff")&&Type!=TEXT("spellbook"))return 0;
    const auto F=Obj(Read(&Item),TEXT("matkFormula"));if(!F)return 0;
    const double L=ColdSteelInventory::Number(Item,TEXT("enhanceLevel"));
    const double Base=CoreCombatFormula::Round(Num(F,TEXT("base"))+L*Num(F,TEXT("enhanceBase"))+Attribute(TEXT("intt"))*(Num(F,TEXT("intMul"))+L*Num(F,TEXT("enhanceIntMul")))+Attribute(TEXT("wis"))*(Num(F,TEXT("wisMul"))+L*Num(F,TEXT("enhanceWisMul"))));
    return CoreCombatFormula::Round(Base*ColdSteelWoodQuality::Multiplier(Item,ColdSteelWoodQuality::EChannel::MagicAttack));
}
const FColdSteelItem* UColdSteelStatusModel::ActiveSpellbook()const
{
    if(ActiveProductionTool())return nullptr;
    const int32 Slot=Current.ActiveWeaponSlot==6?8:11;
    if(ColdSteelInventory::Locked(Current.Items,Slot))return nullptr;
    const auto* Book=Equipped(Slot);
    return Book&&Book->Definition==TEXT("ue_alchemy_spellbook")?Book:nullptr;
}
double UColdSteelStatusModel::EquipmentMagicAttack()const
{
    const auto* Main=Equipped();const auto* Book=ActiveSpellbook();
    return (Main?ItemMagicAttack(*Main):0)+(Book?ItemMagicAttack(*Book):0);
}
void UColdSteelStatusModel::ApplySpellbookFocus(float& CastSpeed,float& ManaCost)const
{
    const auto* Book=ActiveSpellbook();if(!Book)return;
    const auto* Pawn=RuntimePawn();
    const auto* Focus=Pawn?Pawn->FindComponentByClass<USpellbookComponent>():nullptr;
    if(!Focus||!Focus->IsFocusEmpowered())return;
    const auto Effects=Obj(Read(Book),TEXT("focusEffects"));
    CastSpeed*=float(Num(Effects,TEXT("castSpeedMultiplier"),1));
    // Apply after the spell's existing cost modifiers, without an extra integer rounding.
    ManaCost*=float(Num(Effects,TEXT("manaCostMultiplier"),1));
}
float UColdSteelStatusModel::SpellbookFocusMovementMultiplier()const
{
    return float(Num(Obj(Read(ActiveSpellbook()),TEXT("focusEffects")),TEXT("movementMultiplier"),.67));
}
bool UColdSteelStatusModel::ApplySpellbookFocusBreak()
{
    const auto* Book=ActiveSpellbook();if(!Book||HasInfiniteMana())return true;
    const float Fraction=float(Num(Obj(Read(Book),TEXT("focusEffects")),TEXT("interruptMaxManaFraction"),.25));
    // This is a loss, not a cast cost: no affordability gate or focus discount.
    SpellbookFocusMana::Merge(Current,Current.SpellbookFocusManaLoss+Derived(TEXT("maxMp"))*Fraction);
    // Publish the loss immediately and use the existing combat autosave queue;
    // never perform synchronous slot writes or re-equip during the hit reaction.
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    OnChanged.Broadcast();return true;
}
void UColdSteelStatusModel::ReconcileSpellbookFocusManaLoss(double Total)
{
    if(!FMath::IsFinite(Total)||Total<=Current.SpellbookFocusManaLoss)return;
    SpellbookFocusMana::Merge(Current,Total);
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    OnChanged.Broadcast();
}
float UColdSteelStatusModel::CombatMoveMultiplier()const
{return SetEffect(TEXT("speed"))*FMath::Max(.5,1+DungeonEffect(TEXT("moveSpeedPercent"))/100.)*TributeEffect(TEXT("moveSpeedPercent"))*FMath::Max(.5,1.+EquipmentBonus(TEXT("moveSpeedPercent")));}
bool UColdSteelStatusModel::OfferTribute(const FString& Id)
{
    SyncRuntime();auto P=Snapshot();const int32 Index=P.Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id&&(I.Place==0||I.Place==ColdSteelInventory::ColdSteelCompartment::Place)&&I.Count>0;});if(Index<0)return false;
    auto& I=P.Items[Index];if(ColdSteelInventory::Text(I,TEXT("category"))!=TEXT("tribute"))return false;
    const auto E=Obj(Read(&I),TEXT("effects"));if(!E)return false;
    FColdSteelFormulaBuff Buff;Buff.Id=FName(*I.Definition);Buff.bTribute=true;Buff.RemainingSeconds=1800;Buff.Rarity=ColdSteelInventory::Text(I,TEXT("rarity"));
    for(const auto& V:E->Values)if(V.Value->Type==EJson::Number)Buff.Effects.Add(FName(*V.Key),V.Value->AsNumber());
    // 旧 tribute 的 special 块同样随献祭携带（布尔按 1 记），由机制端（金刚石/月影/血藤等）消费。
    if(const auto S=Obj(Read(&I),TEXT("special")))for(const auto& V:S->Values)
    {if(V.Value->Type==EJson::Number)Buff.Specials.Add(FName(*V.Key),V.Value->AsNumber());
     else if(V.Value->Type==EJson::Boolean)Buff.Specials.Add(FName(*V.Key),V.Value->AsBool()?1.f:0.f);}
    P.FormulaBuffs.RemoveAll([&](const auto& B){return B.bTribute&&(B.Rarity==Buff.Rarity||B.RemainingSeconds<=0);});P.FormulaBuffs.Add(Buff);
    if(--I.Count<=0)P.Items.RemoveAt(Index);return CommitState(P);
}
bool UColdSteelStatusModel::ApplyDungeonFormulaBuff(FName Id,const TMap<FName,float>& Effects,int32 Battles)
{
    if(Id.IsNone()||Battles<=0)return false;
    SyncRuntime();auto P=Snapshot();P.FormulaBuffs.RemoveAll([&](const auto& B){return !B.bTribute&&B.Id==Id;});
    FColdSteelFormulaBuff B;B.Id=Id;B.Effects=Effects;B.Battles=Battles;P.FormulaBuffs.Add(B);
    if(!CommitState(P))return false;
    SyncDungeonBattleTiles();return true;
}
bool UColdSteelStatusModel::ApplyDungeonEventBuff(FName Id)
{
    // 旧 _applyTemporaryBuff（dungeon-event-definitions.js:1901-1935）：参数以事件目录为准，默认 3 场。
    static TMap<FName,TPair<TMap<FName,float>,int32>> Catalog;
    if(Catalog.IsEmpty())
    {
        FString Text;TSharedPtr<FJsonObject> Json;
        if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/dungeon_event_buffs.json")))
            &&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Json))
            for(const auto& Pair:Json->Values)
            {
                const TSharedPtr<FJsonObject>* V=nullptr;
                if(!Pair.Value->TryGetObject(V))continue;
                TMap<FName,float> Effects;double Battles=3;
                if(const TSharedPtr<FJsonObject>* F=nullptr;(*V)->TryGetObjectField(TEXT("effects"),F))
                    for(const auto& Field:(*F)->Values)if(Field.Value->Type==EJson::Number)Effects.Add(FName(*Field.Key),Field.Value->AsNumber());
                (*V)->TryGetNumberField(TEXT("battles"),Battles);
                Catalog.Add(FName(*Pair.Key),{MoveTemp(Effects),FMath::Max(1,FMath::RoundToInt(Battles))});
            }
    }
    const auto* E=Catalog.Find(Id);
    return E?ApplyDungeonFormulaBuff(Id,E->Key,E->Value):false;
}
bool UColdSteelStatusModel::CompleteDungeonFormulaBattle()
{
    SyncRuntime();auto P=Snapshot();for(auto& B:P.FormulaBuffs)if(!B.bTribute)--B.Battles;
    P.FormulaBuffs.RemoveAll([](const auto& B){return !B.bTribute&&B.Battles<=0;});
    if(!CommitState(P))return false;
    SyncDungeonBattleTiles();return true;
}
void UColdSteelStatusModel::SyncDungeonBattleTiles()
{
    // 旧 2.34/2.45：地牢事件 buff 以自身 ID 作卡片 type、「N场」倒计时展示，逐场消耗；
    // 目录门（HasType）确保 dungeon_relay 等无目录条目 ID 不渲染 "?" 卡；diff 发布避免逐帧广播。
    TMap<FName,int32> Active;
    for(const auto& B:Current.FormulaBuffs)if(!B.bTribute&&B.Battles>0&&!B.Id.IsNone()&&UStatusEffectsComponent::HasType(B.Id))
        Active.FindOrAdd(B.Id)=FMath::Max(Active.FindRef(B.Id),B.Battles);
    auto* Pawn=CurrentPawn.Get();
    if(auto* Display=IsValid(Pawn)?UStatusEffectsComponent::GetOrCreate(Pawn):nullptr)
    {
        for(const auto& Pair:PublishedDungeonTiles)if(!Active.Contains(Pair.Key))Display->Remove(Pair.Key);
        for(const auto& Pair:Active){const int32* Prev=PublishedDungeonTiles.Find(Pair.Key);if(!Prev||*Prev!=Pair.Value)Display->SetBattles(Pair.Key,Pair.Value);}
    }
    PublishedDungeonTiles=MoveTemp(Active);
}

void UColdSteelStatusModel::TickFormulaBuffs(float Delta)
{
    for(auto& B:Current.FormulaBuffs)if(B.bTribute)B.RemainingSeconds-=Delta;
    if(Current.FormulaBuffs.RemoveAll([](const auto& B){return B.bTribute&&B.RemainingSeconds<=0;})>0){SyncRuntime();ApplyToPawn();}
    SyncTributeTiles();
    SyncDungeonBattleTiles();
}
