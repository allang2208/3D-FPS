#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"
#include "Misc/DateTime.h"
#include "Serialization/JsonSerializer.h"
#include "CoreCombatFormula.h"
#include "CombatItemFormula.h"
namespace
{
using J=TSharedPtr<FJsonObject>;
J Read(const FColdSteelItem* I){return I?CombatItemFormula::Read(*I):nullptr;}
J Obj(J O,const TCHAR* K){const J* V=nullptr;return O&&O->TryGetObjectField(K,V)?*V:nullptr;}
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
double UColdSteelStatusModel::DungeonEffect(FName Key)const
{
    double Total=0;for(const auto& B:Current.FormulaBuffs)if(!B.bTribute&&B.Battles>0)Total+=B.Effects.FindRef(Key);return Total;
}
double UColdSteelStatusModel::AdjustCombatStat(FName Key,double Value)const
{
    if(Key==TEXT("atk"))Value=std::floor(Value*(1+SetEffect(TEXT("atk"))));
    if(Key==TEXT("crit"))Value+=SetEffect(TEXT("crit"));
    const FName Percent(*(Key.ToString()+TEXT("Percent")));
    if(Key==TEXT("atk")||Key==TEXT("matk")||Key==TEXT("def"))Value=std::floor(Value*(1+DungeonEffect(Percent)/100.));
    if(Key==TEXT("atk")||Key==TEXT("matk")||Key==TEXT("def")||Key==TEXT("mdef")||Key==TEXT("crit"))Value=std::floor(Value*TributeEffect(Percent));
    return Value;
}
double UColdSteelStatusModel::EquipmentMagicAttack()const
{
    const auto* I=Equipped();if(!I||ColdSteelInventory::Text(*I,TEXT("weaponType"))!=TEXT("staff"))return 0;
    const auto F=Obj(Read(I),TEXT("matkFormula"));if(!F)return 0;
    const double L=ColdSteelInventory::Number(*I,TEXT("enhanceLevel"));
    return CoreCombatFormula::Round(Num(F,TEXT("base"))+L*Num(F,TEXT("enhanceBase"))+Attribute(TEXT("intt"))*(Num(F,TEXT("intMul"))+L*Num(F,TEXT("enhanceIntMul")))+Attribute(TEXT("wis"))*(Num(F,TEXT("wisMul"))+L*Num(F,TEXT("enhanceWisMul"))));
}
float UColdSteelStatusModel::CombatMoveMultiplier()const
{return SetEffect(TEXT("speed"))*FMath::Max(.5,1+DungeonEffect(TEXT("moveSpeedPercent"))/100.)*TributeEffect(TEXT("moveSpeedPercent"));}
bool UColdSteelStatusModel::OfferTribute(const FString& Id)
{
    SyncRuntime();auto P=Snapshot();const int32 Index=P.Items.IndexOfByPredicate([&](const auto& I){return I.InstanceId==Id&&I.Place==0&&I.Count>0;});if(Index<0)return false;
    auto& I=P.Items[Index];if(ColdSteelInventory::Text(I,TEXT("category"))!=TEXT("tribute"))return false;
    const auto E=Obj(Read(&I),TEXT("effects"));if(!E)return false;
    FColdSteelFormulaBuff Buff;Buff.Id=FName(*I.Definition);Buff.bTribute=true;Buff.RemainingSeconds=1800;Buff.Rarity=ColdSteelInventory::Text(I,TEXT("rarity"));
    for(const auto& V:E->Values)if(V.Value->Type==EJson::Number)Buff.Effects.Add(FName(*V.Key),V.Value->AsNumber());
    P.FormulaBuffs.RemoveAll([&](const auto& B){return B.bTribute&&(B.Rarity==Buff.Rarity||B.RemainingSeconds<=0);});P.FormulaBuffs.Add(Buff);
    if(--I.Count<=0)P.Items.RemoveAt(Index);return CommitState(P);
}
bool UColdSteelStatusModel::ApplyDungeonFormulaBuff(FName Id,const TMap<FName,float>& Effects,int32 Battles)
{
    if(Id.IsNone()||Battles<=0)return false;
    SyncRuntime();auto P=Snapshot();P.FormulaBuffs.RemoveAll([&](const auto& B){return !B.bTribute&&B.Id==Id;});
    FColdSteelFormulaBuff B;B.Id=Id;B.Effects=Effects;B.Battles=Battles;P.FormulaBuffs.Add(B);return CommitState(P);
}
bool UColdSteelStatusModel::CompleteDungeonFormulaBattle()
{
    SyncRuntime();auto P=Snapshot();for(auto& B:P.FormulaBuffs)if(!B.bTribute)--B.Battles;
    P.FormulaBuffs.RemoveAll([](const auto& B){return !B.bTribute&&B.Battles<=0;});return CommitState(P);
}

void UColdSteelStatusModel::TickFormulaBuffs(float Delta)
{
    for(auto& B:Current.FormulaBuffs)if(B.bTribute)B.RemainingSeconds-=Delta;
    if(Current.FormulaBuffs.RemoveAll([](const auto& B){return B.bTribute&&B.RemainingSeconds<=0;})>0){SyncRuntime();ApplyToPawn();}
}
