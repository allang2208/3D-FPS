#include "ColdSteelEnhancementSystem.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/CombatItemFormula.h"

namespace
{
using J=TSharedPtr<FJsonObject>;
J Read(const FString& S){J O;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(S),O);return O;}
J Obj(J O,const TCHAR* Key){const J* V=nullptr;return O&&O->TryGetObjectField(Key,V)?*V:nullptr;}
double Num(TSharedPtr<const FJsonObject> O,const TCHAR* Key,double D=0){double V;return O&&O->TryGetNumberField(Key,V)?V:D;}
FString Str(J O,const TCHAR* Key){FString V;if(O)O->TryGetStringField(Key,V);return V;}
void Write(FColdSteelItem& I,J O){FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&I.Data));}
}
void UColdSteelEnhancementSystem::Initialize(FSubsystemCollectionBase& C)
{
    Super::Initialize(C);C.InitializeDependency<UColdSteelStatusModel>();C.InitializeDependency<UGunsmithSystem>();
    FString FormulaText;
    if(FFileHelper::LoadFileToString(FormulaText,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/combat-weapon-formulas.json"))))WeaponFormulas=Read(FormulaText);
    FString S;if(!FFileHelper::LoadFileToString(S,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/enhancement.json"))))return;
    const auto Root=Read(S);if(!Root)return;
    WeaponMax=Num(Root,TEXT("maxWeaponLevel"),15);ArmorMax=Num(Root,TEXT("maxArmorLevel"),10);
    BaseGold=Num(Root,TEXT("baseGold"),100);Growth=Num(Root,TEXT("goldGrowth"),1.5);Stones=Num(Root,TEXT("stones"),1);Increase=Num(Root,TEXT("weaponIncreasePerLevel"),.05);
    const TArray<TSharedPtr<FJsonValue>>* List=nullptr;if(!Root->TryGetArrayField(TEXT("scrolls"),List))return;
    for(const auto& V:*List){const auto O=V->AsObject();if(!O)continue;Options.Add({Str(O,TEXT("id")),Str(O,TEXT("item")),Str(O,TEXT("name")),Str(O,TEXT("slot")),Str(O,TEXT("restriction")),Str(O,TEXT("description")),int64(Num(O,TEXT("dust"))),Obj(O,TEXT("effects"))});}
    Ready=WeaponMax>0&&WeaponMax<=100&&ArmorMax>0&&BaseGold>0&&Growth>=1&&Growth<=2&&Increase>0&&Increase<=1&&Stones>0;
}
bool UColdSteelEnhancementSystem::Supports(const FColdSteelItem& I)const
{
    if(!Ready||I.Count!=1||(I.Place!=0&&I.Place!=1))return false;
    if(GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Weapon(I.Definition))return true;
    return Num(Obj(CombatItemFormula::Read(I),TEXT("defense")),TEXT("perEnhance"))>0;
}
bool UColdSteelEnhancementSystem::CanEnchant(const FColdSteelItem& I,const FColdSteelEnchantOption& O)const
{
    if(!Supports(I)||!GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Weapon(I.Definition))return false;
    return O.Restriction==TEXT("firearm")||O.Restriction==TEXT("weapon");
}
const FColdSteelEnchantOption* UColdSteelEnhancementSystem::Scroll(const FString& Id)const{return Options.FindByPredicate([&](const auto& O){return O.Id==Id;});}
int32 UColdSteelEnhancementSystem::MaxLevel(const FColdSteelItem& I)const{return GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Weapon(I.Definition)?WeaponMax:ArmorMax;}
double UColdSteelEnhancementSystem::Effect(const FColdSteelItem& I,const TCHAR* Key,double Default)const
{
    const auto O=Obj(Read(I.Data),TEXT("_enchantEffects"));
    const auto V=O?O->TryGetField(Key):nullptr;
    if(V&&V->Type==EJson::Boolean)return V->AsBool()?1:0;
    return Num(O,Key,Default);
}
double UColdSteelEnhancementSystem::CraftEffect(const FColdSteelItem& I,const TCHAR* Key,double Default)const
{return Num(Obj(Read(I.Data),TEXT("_craftEffects")),Key,Default);}
TSharedPtr<const FJsonObject> UColdSteelEnhancementSystem::AttackFormula(const FColdSteelItem& I)const
{
    if(const auto Formula=Obj(WeaponFormulas,*I.Definition))return Formula;
    return Obj(CombatItemFormula::Read(I),TEXT("attackFormula"));
}
double UColdSteelEnhancementSystem::AttackFormulaAttribute(const FColdSteelItem& I,FName Key)const
{
    if(Key==TEXT("int"))Key=TEXT("intt");
    const auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    // Match raw allocated + equipment attributes used by the original weapon formulas.
    return double(P->Attributes.FindRef(Key))+P->EquipmentBonus(Key)+(Key==TEXT("str")&&P->WeaponMastery(&I)==TEXT("swordMastery")?P->MasteryEffect(TEXT("heavyStrike")).Strength:0);
}
double UColdSteelEnhancementSystem::ProcessedDamage(const FColdSteelItem& I,double Base,double Attack)const
{
    const double L=FMath::Clamp(ColdSteelInventory::Number(I,TEXT("enhanceLevel")),0.,double(WeaponMax));
    if(const auto Formula=AttackFormula(I))
    {
        const auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        std::vector<CoreCombatFormula::WeaponTerm> Terms;
        for(const auto& V:Formula->GetArrayField(TEXT("attrs")))
        {
            const auto T=V->AsObject();const FName Key(*Str(T,TEXT("key")));
            Terms.push_back({AttackFormulaAttribute(I,Key),Num(T,TEXT("base")),Num(T,TEXT("perEnhance"))});
        }
        double Result=CoreCombatFormula::Weapon(Num(Formula,TEXT("base")),Num(Formula,TEXT("enhanceFlat")),L,Terms);
        // Keep current gunsmith part ratios while replacing the obsolete native damage baseline.
        if(const auto* W=GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Weapon(I.Definition))
            Result=CoreCombatFormula::Round(Result*Base/W->Base.Damage);
        Result=CoreCombatFormula::Round(Result*(1+CraftEffect(I,TEXT("damagePercent"))));
        Result=P->AdditionalWeaponDamage(I,Result);
        return CoreCombatFormula::Round(Result*(1+Effect(I,TEXT("damagePercent"))));
    }
    return (Base*(1+L*Increase)+Attack)*(1+FMath::Clamp(Effect(I,TEXT("damagePercent")),0.,10.));
}
double UColdSteelEnhancementSystem::Defense(const FColdSteelItem& I)const
{
    const auto D=Obj(CombatItemFormula::Read(I),TEXT("defense"));return FMath::FloorToDouble(Num(D,TEXT("base"))+Num(D,TEXT("perEnhance"))*FMath::Clamp(ColdSteelInventory::Number(I,TEXT("enhanceLevel")),0.,double(ArmorMax)));
}
FString UColdSteelEnhancementSystem::Affix(const FColdSteelItem& I,const TCHAR* Slot)const{return Str(Obj(Obj(Read(I.Data),TEXT("_enchantData")),Slot),TEXT("name"));}
int64 UColdSteelEnhancementSystem::BackpackScrollCount(const FString& Definition)const
{
    int64 Count=0;
    for(const auto& Item:GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->Items())
        if(Item.Place==0&&Item.Definition==Definition&&Item.Count>0)Count+=Item.Count;
    return Count;
}
FColdSteelEnhanceQuote UColdSteelEnhancementSystem::Quote(const FString& Id,const FString& ScrollId)const
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();FColdSteelEnhanceQuote Q;Q.ItemId=Id;Q.ScrollId=ScrollId;Q.Revision=P->Snapshot().Generation;
    Q.Reason=TEXT("请选择可强化的装备");const auto* I=P->FindItem(Id);if(!I||!Supports(*I))return Q;
    Q.Before=*I;Q.After=*I;auto Data=Read(I->Data);if(!Data)return Q;
    auto Cost=[&](const FString& Def,int64 Need,bool BackpackOnly=false){Q.Costs.Add({Def,ColdSteelInventory::Text(P->CreateItem(Def),TEXT("name")),Need,BackpackOnly?BackpackScrollCount(Def):P->CountMaterial(Def),BackpackOnly});};
    if(ScrollId.IsEmpty())
    {
        const int32 Level=ColdSteelInventory::Number(*I,TEXT("enhanceLevel"));
        if(Level<0||Level>=MaxLevel(*I)){Q.Reason=TEXT("已达到强化上限");return Q;}
        Cost(TEXT("enhancement_stone"),Stones);Cost(TEXT("gold"),int64(FMath::FloorToDouble(BaseGold*FMath::Pow(Growth,Level))));
        Data->SetNumberField(TEXT("enhanceLevel"),Level+1);
    }
    else
    {
        const auto* O=Scroll(ScrollId);if(!O||!CanEnchant(*I,*O)){Q.Reason=TEXT("卷轴与该装备不兼容");return Q;}
        auto Enchant=Obj(Data,TEXT("_enchantData"));if(!Enchant)Enchant=MakeShared<FJsonObject>();
        if(Str(Obj(Enchant,*O->Slot),TEXT("id"))==O->Id){Q.Reason=TEXT("已拥有相同词缀");return Q;}
        Cost(O->Item,1,true);Cost(TEXT("magic_dust"),O->Dust);
        auto AffixData=MakeShared<FJsonObject>();AffixData->SetStringField(TEXT("id"),O->Id);AffixData->SetStringField(TEXT("name"),O->Name);AffixData->SetObjectField(TEXT("effects"),O->Effects);
        Enchant->SetObjectField(O->Slot,AffixData);Data->SetObjectField(TEXT("_enchantData"),Enchant);
        // Rebuild from the two surviving slots. Replacing a suffix removes its previous effects.
        auto Effects=MakeShared<FJsonObject>();
        for(const TCHAR* Slot:{TEXT("prefix"),TEXT("suffix")})if(auto A=Obj(Enchant,Slot)){
            auto E=Obj(A,TEXT("effects"));if(!E)if(const auto* Existing=Scroll(Str(A,TEXT("id"))))E=Existing->Effects;
            if(E)for(const auto& Pair:E->Values){const FString Key(*Pair.Key);if(Pair.Value->Type==EJson::Number){const bool Mul=Key==TEXT("attackIntervalMul");Effects->SetNumberField(Key,Mul?Num(Effects,*Key,1)*Pair.Value->AsNumber():Num(Effects,*Key)+Pair.Value->AsNumber());}else Effects->SetField(Key,Pair.Value);}
        }
        Data->SetObjectField(TEXT("_enchantEffects"),Effects);Data->SetBoolField(TEXT("_isEnchanted"),true);
    }
    Write(Q.After,Data);Q.Valid=true;Q.Reason=TEXT("材料充足");
    for(const auto& C:Q.Costs)if(C.Have<C.Need){Q.Valid=false;Q.Reason=TEXT("材料不足：")+C.Name;break;}
    return Q;
}
bool UColdSteelEnhancementSystem::Apply(const FColdSteelEnhanceQuote& Expected,FString& Message)
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Expected.Revision!=P->Snapshot().Generation){Message=TEXT("物品或材料已变化，请重新确认");return false;}
    P->SyncRuntime();const auto Q=Quote(Expected.ItemId,Expected.ScrollId);if(!Q.Valid){Message=Q.Reason;return false;}
    auto Next=P->Snapshot();auto* I=Next.Items.FindByPredicate([&](const auto& V){return V.InstanceId==Q.ItemId;});if(!I)return false;
    // Only processing JSON changes: identity, cells, ammo, cooldown, attachments stay intact.
    I->Data=Q.After.Data;
    for(const auto& C:Q.Costs){int64 Left=C.Need;for(int32 Place:{0,4}){if(C.BackpackOnly&&Place!=0)continue;for(auto& M:Next.Items)if(M.Place==Place&&M.Definition==C.Definition&&Left>0){const int64 Used=FMath::Min(Left,M.Count);M.Count-=Used;Left-=Used;}}if(Left){Message=TEXT("材料已变化");return false;}}
    Next.Items.RemoveAll([](const auto& V){return V.Count<=0;});
    if(!P->CommitState(Next)){Message=P->ResultMessage();return false;}Message=Q.ScrollId.IsEmpty()?TEXT("强化成功，已保存"):TEXT("附魔成功，已保存");return true;
}
