#include "ColdSteelItemTooltipData.h"
#include "../Combat/CombatItemFormula.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/RuneSwordRhythm.h"
#include "../Weapons/RuneSwordThrustRhythm.h"
#include "../Weapons/RuneSwordCombatTuning.h"
#include "../Weapons/RuneSwordGuardTuning.h"
#include "../FPSGAMECharacter.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UObject/UnrealType.h"

namespace
{
using J=TSharedPtr<FJsonObject>;
J Object(const J& O,const TCHAR* Key){const J* V=nullptr;return O&&O->TryGetObjectField(Key,V)?*V:nullptr;}
FString String(const J& O,const TCHAR* Key,const FString& Default=TEXT("")){FString V;return O&&O->TryGetStringField(Key,V)?V:Default;}
double Number(const J& O,const TCHAR* Key,double Default=0){double V;return O&&O->TryGetNumberField(Key,V)?V:Default;}
FString N(double V){FString S=FString::Printf(TEXT("%.2f"),V);while(S.EndsWith(TEXT("0")))S.LeftChopInline(1);if(S.EndsWith(TEXT(".")))S.LeftChopInline(1);return S==TEXT("-0")?TEXT("0"):S;}
float Field(const UObject* O,const TCHAR* Key){const auto* P=FindFProperty<FFloatProperty>(O->GetClass(),Key);return P?P->GetPropertyValue_InContainer(O):0;}
FString Signed(double V,const TCHAR* Unit=TEXT("")){return (V>0?TEXT("+"):TEXT(""))+N(V)+Unit;}
FString Value(const TSharedPtr<FJsonValue>& V){if(!V)return TEXT("");if(V->Type==EJson::String)return V->AsString();if(V->Type==EJson::Number)return N(V->AsNumber());if(V->Type==EJson::Boolean)return V->AsBool()?TEXT("是"):TEXT("否");return TEXT("");}
void Row(FColdSteelTooltipCard& C,const FString& Label,const FString& Val,int32 Tone=0){if(!Val.IsEmpty())C.Rows.Add({Label,Val,Tone,false});}
void Section(FColdSteelTooltipCard& C,const FString& Label){C.Rows.Add({Label,TEXT(""),0,true});}
FString Category(const FString& K){static const TMap<FString,FString> M={{TEXT("weapon_ranged"),TEXT("远程武器")},{TEXT("weapon_melee"),TEXT("近战武器")},{TEXT("armor"),TEXT("防具")},{TEXT("accessory"),TEXT("饰品")},{TEXT("consumable"),TEXT("消耗品")},{TEXT("material"),TEXT("材料")},{TEXT("enhancement"),TEXT("强化材料")},{TEXT("tribute"),TEXT("贡品")},{TEXT("gold"),TEXT("金币")}};const auto* V=M.Find(K);return V?*V:K;}
void Delta(FColdSteelTooltipCard& C,const FString& Label,double V,const TCHAR* Unit,bool Lower=false){if(FMath::Abs(V)>.00001)Row(C,Label,Signed(V,Unit),(V>0)!=Lower?1:-1);}
J Reference(){static J Root;static bool Loaded=false;if(!Loaded){Loaded=true;FString Text;if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/tooltip-reference.json"))))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root);}return Root;}
}

FColdSteelTooltipContent BuildColdSteelItemTooltip(const FColdSteelItem& I,UColdSteelStatusModel* Model,UGunsmithSystem* G)
{
    FColdSteelTooltipContent Out;J O;
    O=CombatItemFormula::Read(I);if(!O)return Out;
    Out.Name=String(O,TEXT("name"),I.Definition);Out.Type=String(O,TEXT("type"),Category(String(O,TEXT("category"))));
    Out.Rarity=String(O,TEXT("rarity"),TEXT("common"));Out.Level=Number(O,TEXT("level"));Out.Icon=String(O,TEXT("ue_icon"));Out.Description=String(O,TEXT("desc"));
    const int32 Enhance=Number(O,TEXT("enhanceLevel"));if(Enhance>0)Out.Enhancement=FString::Printf(TEXT("已强化 +%d"),Enhance);
    auto Damage=[&](double Base){return ColdSteelWeaponStats::Damage(I,Model,Base);};

    const J Enchant=Object(O,TEXT("_enchantData"));const J EE=Object(O,TEXT("_enchantEffects"));
    if(Enchant&&(Object(Enchant,TEXT("prefix"))||Object(Enchant,TEXT("suffix")))){
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("附魔效果");C.MinimumWidth=300;
        FString Name=String(Object(Enchant,TEXT("prefix")),TEXT("name"));
        const FString Suffix=String(Object(Enchant,TEXT("suffix")),TEXT("name"));if(!Suffix.IsEmpty()){if(!Name.IsEmpty())Name+=TEXT(" · ");Name+=Suffix;}
        Row(C,TEXT("当前词缀"),Name);
        if(EE){Delta(C,TEXT("攻击力"),Number(EE,TEXT("damagePercent"))*100,TEXT("%"));
            if(EE->HasField(TEXT("attackIntervalMul")))Row(C,TEXT("攻击间隔"),TEXT("×")+N(Number(EE,TEXT("attackIntervalMul"))),Number(EE,TEXT("attackIntervalMul"))<1?1:-1);
            Delta(C,TEXT("暴击率"),Number(EE,TEXT("critRate"))*100,TEXT("%"));Delta(C,TEXT("穿透目标"),Number(EE,TEXT("piercingBonus")),TEXT("个"));
            bool Poison=false;if(EE->TryGetBoolField(TEXT("poisonOnHit"),Poison)&&Poison)Row(C,TEXT("特殊效果"),TEXT("攻击叠加中毒"),1);}
    }
    const auto* Weapon=G?G->Weapon(I.Definition):nullptr;const FGunsmithParts Parts=Weapon?G->Installed(I):FGunsmithParts();
    bool Installed=false;for(const auto& P:Parts)if(G->Option(I.Definition,P.Key,P.Value))Installed=true;
    const J Craft=Object(O,TEXT("_craftData")),CE=Object(O,TEXT("_craftEffects"));
    if(Installed||(Craft&&!Craft->Values.IsEmpty())){
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("改造项目");C.MinimumWidth=600;
        if(Installed){for(const auto& Slot:G->Slots())if(const auto* Id=Parts.Find(Slot))if(const auto* P=G->Option(I.Definition,Slot,*Id)){
                Section(C,P->Name);
                if(P->Effects.IsEmpty())Row(C,TEXT(""),P->Description);
                else for(const auto& E:P->Effects)Row(C,TEXT(""),E.Key,E.Value);
                C.Rows.Last().bDashedAfter=true;}
            const auto S=G->Calculate(I.Definition,Parts),B=G->Calculate(I.Definition,{});Section(C,TEXT("合计改造数值"));
            Delta(C,TEXT("伤害"),S.Damage-B.Damage,TEXT(""));Delta(C,TEXT("弹匣容量"),S.Capacity-B.Capacity,TEXT("发"));
            Delta(C,TEXT("瞄准耗时"),(S.ADS-B.ADS)*1000,TEXT("ms"),true);Delta(C,TEXT("射击间隔"),(S.Interval-B.Interval)*1000,TEXT("ms"),true);
            Delta(C,TEXT("普通换弹"),(S.Reload-B.Reload)*1000,TEXT("ms"),true);Delta(C,TEXT("空仓换弹"),(S.EmptyReload-B.EmptyReload)*1000,TEXT("ms"),true);
            Delta(C,TEXT("后坐力指数"),S.Recoil-B.Recoil,TEXT(""),true);Delta(C,TEXT("枪械稳定性"),S.Handling.Stability-B.Handling.Stability,TEXT("分"));
            Delta(C,TEXT("枪械稳定性·回稳90%"),S.Handling.ADSRecoveryMilliseconds()-B.Handling.ADSRecoveryMilliseconds(),TEXT("ms"),true);
            if(B.Spread>0)Delta(C,TEXT("腰射散布"),(S.Spread/B.Spread-1)*100,TEXT("%"),true);
            Delta(C,TEXT("射程"),S.Range-B.Range,TEXT("m"));Delta(C,TEXT("弹速"),S.Speed-B.Speed,TEXT("m/s"));}
        if(Craft){const auto Config=Object(Object(Reference(),TEXT("craft")),*I.Definition);const auto Options=Object(Config,TEXT("options"));
            for(const auto& P:Craft->Values){const TArray<TSharedPtr<FJsonValue>>* List=nullptr;if(!Options||!Options->TryGetArrayField(FString(*P.Key),List))continue;
                for(const auto& V:*List){const auto Option=V->AsObject();if(String(Option,TEXT("id"))==Value(P.Value)){Section(C,String(Option,TEXT("name")));Row(C,TEXT(""),String(Option,TEXT("desc")));C.Rows.Last().bDashedAfter=true;break;}}}}
        if(CE&&!CE->Values.IsEmpty()){
            Section(C,TEXT("合计改造数值"));
            struct FEffect{const TCHAR* Key;const TCHAR* Label;const TCHAR* Unit;double Scale;bool Lower;};
            const FEffect Effects[]={{TEXT("damagePercent"),TEXT("伤害"),TEXT("%"),100,false},{TEXT("piercingBonus"),TEXT("穿透目标"),TEXT("个"),1,false},{TEXT("critChancePercent"),TEXT("暴击率"),TEXT("%"),100,false},{TEXT("rangeDelta"),TEXT("攻击距离"),TEXT("px"),1,false},{TEXT("projectileSpeedPercent"),TEXT("弹速"),TEXT("%"),100,false},{TEXT("moveSpeedPercent"),TEXT("移速"),TEXT("%"),100,false},{TEXT("attackIntervalDelta"),TEXT("攻击间隔"),TEXT("ms"),1,true},{TEXT("magazineDelta"),TEXT("弹容量"),TEXT("发"),1,false},{TEXT("magazinePercent"),TEXT("弹容量"),TEXT("%"),100,false},{TEXT("reloadTimeDelta"),TEXT("换弹耗时"),TEXT("ms"),1,true},{TEXT("maxSpreadAngleDelta"),TEXT("最大散布"),TEXT("°"),1,true},{TEXT("defensePercent"),TEXT("防御"),TEXT("%"),100,false},{TEXT("staminaCostDelta"),TEXT("体力消耗"),TEXT(""),1,true},{TEXT("knockbackDelta"),TEXT("击退距离"),TEXT("px"),1,false}};
            for(const auto& E:Effects)Delta(C,E.Label,Number(CE,E.Key)*E.Scale,E.Unit,E.Lower);
        }
    }
    auto& Main=Out.Cards.AddDefaulted_GetRef();Main.MinimumWidth=460;
    const TArray<TSharedPtr<FJsonValue>>* Stats=nullptr;
    FGunsmithStats S;if(Weapon)S=G->Calculate(I.Definition,Parts);
    if(O->TryGetArrayField(TEXT("stats"),Stats))for(const auto& V:*Stats){const auto St=V->AsObject();const FString Label=String(St,TEXT("name"),String(St,TEXT("label")));FString Val=St->HasField(TEXT("value"))?Value(St->Values[TEXT("value")]):TEXT("");
        if((Weapon||I.Definition==TEXT("ue_rune_sword"))&&Label==TEXT("物理攻击"))continue;
        if(Weapon&&Label==TEXT("弹匣容量"))continue;
        if(!Weapon&&I.Definition==TEXT("ue_m4a1")&&Label==TEXT("物理攻击"))Val=N(Damage(Field(GetDefault<AFPSGAMECharacter>(),TEXT("DamagePerShot"))));
        bool Positive=false;St->TryGetBoolField(TEXT("pos"),Positive);if(!Label.IsEmpty())Row(Main,Label,Val,Positive?1:0);}
    Section(Main,TEXT("物品信息"));Row(Main,TEXT("分类"),Category(String(O,TEXT("category"))));
    Row(Main,TEXT("武器类型"),String(O,TEXT("weaponTypeTag"),String(O,TEXT("weaponType"))));Row(Main,TEXT("装备槽位"),String(O,TEXT("equipSlot")));
    const FString Cat=String(O,TEXT("category"));const J Attack=Object(O,TEXT("attack")),Defense=Object(O,TEXT("defense"));
    if(I.Definition==TEXT("ue_rune_sword")){
        Section(Main,TEXT("近战参数"));AppendColdSteelTooltipAttackFormula(I,Model,Number(O,TEXT("melee_damage"),55),Main);
        auto* EnhanceSystem=Model?Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
        const double Rate=FMath::Clamp((Model?double(Model->Derived(TEXT("aspd"))):1.)/FMath::Max(.1,EnhanceSystem?EnhanceSystem->Effect(I,TEXT("attackIntervalMul"),1):1.)/(Model?1-Model->MasteryEffect(TEXT("swordMastery")).CooldownReduction:1.),.2,4.);
        Row(Main,TEXT("攻击间隔"),N(RuneSwordRhythm::AttackEnd/Rate)+TEXT(" s"));
        Row(Main,TEXT("突刺时间"),N(RuneSwordThrustRhythm::AttackEnd/Rate)+TEXT(" s"));
        Row(Main,TEXT("最大攻击距离"),N(RuneSwordCombatTuning::ScaledReach(Number(O,TEXT("melee_reach_cm"),180),RuneSwordThrustRhythm::ReachBonus)/100)+TEXT(" m"));
        Row(Main,TEXT("普通挥砍距离"),N(RuneSwordCombatTuning::ScaledReach(Number(O,TEXT("melee_reach_cm"),180))/100)+TEXT(" m"));
        Row(Main,TEXT("每次格挡体力"),N(RuneSwordGuardTuning::BlockStamina));
        Row(Main,TEXT("握持"),TEXT("双手 · 占用副手槽"));
    }else if(Weapon){Section(Main,TEXT("枪械参数"));AppendColdSteelTooltipAttackFormula(I,Model,S.Damage,Main);
        Row(Main,TEXT("子弹数"),FString::Printf(TEXT("%d / %d 发"),I.Magazine,S.Capacity));Row(Main,TEXT("弹药"),ColdSteelWeaponStats::AmmoName(Weapon->Ammo));
        Row(Main,TEXT("攻击间隔"),N(FMath::RoundToInt(ColdSteelWeaponStats::Interval(&I,Model,S.Interval)*1000))+TEXT(" ms"));
        const double FireInterval=ColdSteelWeaponStats::Interval(&I,Model,S.Interval);
        Row(Main,TEXT("理论射速"),FireInterval>0?N(60./FireInterval)+TEXT(" 发/分"):TEXT("—"));
        Row(Main,TEXT("正常换弹"),N(ColdSteelWeaponStats::Reload(&I,Model,S.Reload))+TEXT(" s"));Row(Main,TEXT("空仓换弹"),N(ColdSteelWeaponStats::Reload(&I,Model,S.EmptyReload))+TEXT(" s"));
        Row(Main,TEXT("瞄准耗时"),N(FMath::RoundToInt(S.ADS*1000))+TEXT("ms"));Row(Main,TEXT("后坐力（越低越好）"),N(S.Recoil));Row(Main,TEXT("枪械稳定性（越高越好）"),N(S.Handling.Stability)+TEXT(" /100"));
        Row(Main,TEXT("首发上跳"),FString::Printf(TEXT("%.3f°"),S.Handling.FirstShotDegrees()));
        Row(Main,TEXT("连射上跳/发"),FString::Printf(TEXT("%.3f°"),S.Handling.MaxVerticalDegrees()));
        Row(Main,TEXT("ADS首发水平/发"),FString::Printf(TEXT("%.3f°"),S.Handling.FirstHorizontalDegrees()));
        Row(Main,TEXT("ADS水平上限/发"),FString::Printf(TEXT("%.3f°"),S.Handling.MaxHorizontalDegrees()));
        Row(Main,TEXT("枪械稳定性·回稳90%"),N(FMath::RoundToInt(S.Handling.ADSRecoveryMilliseconds()))+TEXT("ms"));
        Row(Main,TEXT("有效射程"),N(S.Range)+TEXT(" m"));
        Row(Main,TEXT("子弹速度"),S.Speed<=0?TEXT("即时命中"):N(S.Speed)+TEXT("m/s"));
        Row(Main,TEXT("腰射散布倍率"),N(S.Spread)+TEXT("×"));
    }else if(I.Definition==TEXT("ue_m4a1")){
        Section(Main,TEXT("枪械参数"));const auto* D=GetDefault<AFPSGAMECharacter>();
        Row(Main,TEXT("当前伤害"),N(Damage(S.Damage)));Row(Main,TEXT("子弹数"),FString::Printf(TEXT("%d / %d 发"),I.Magazine,D->GetMagazineCapacity()));
        Row(Main,TEXT("攻击间隔"),N(FMath::RoundToInt(ColdSteelWeaponStats::Interval(&I,Model,S.Interval)*1000))+TEXT(" ms"));
        Row(Main,TEXT("普通换弹"),N(ColdSteelWeaponStats::Reload(&I,Model,Field(D,TEXT("ReloadDuration"))))+TEXT(" s"));Row(Main,TEXT("空仓换弹"),N(ColdSteelWeaponStats::Reload(&I,Model,Field(D,TEXT("EmptyReloadDuration"))))+TEXT(" s"));Row(Main,TEXT("瞄准耗时"),N(FMath::RoundToInt(Field(D,TEXT("ADSInDuration"))*1000))+TEXT("ms"));
    }else if(Attack){Section(Main,TEXT("攻击参数"));
        const struct{const TCHAR* Key;const TCHAR* Label;const TCHAR* Unit;} Fields[]={{TEXT("range"),TEXT("攻击距离"),TEXT("px")},{TEXT("bulletSpeed"),TEXT("子弹速度"),TEXT("px/s")},{TEXT("projectileSpeed"),TEXT("投射速度"),TEXT("px/s")},{TEXT("attackInterval"),TEXT("攻击间隔"),TEXT("ms")},{TEXT("knockback"),TEXT("击退距离"),TEXT("px")}};
        for(const auto& F:Fields)if(Attack->HasField(F.Key))Row(Main,F.Label,N(Number(Attack,F.Key))+F.Unit);Row(Main,TEXT("伤害类型"),String(Attack,TEXT("damageType")));Row(Main,TEXT("命中类型"),String(Attack,TEXT("hitType")));
        const auto Ammo=Object(O,TEXT("ammoConfig"));if(Ammo){Section(Main,TEXT("枪械参数"));if(Ammo->HasField(TEXT("max")))Row(Main,TEXT("子弹数"),Value(Ammo->Values[TEXT("max")])+TEXT("发"));if(Ammo->HasField(TEXT("reloadTime")))Row(Main,TEXT("换弹时间"),N(Number(Ammo,TEXT("reloadTime")))+TEXT("ms"));}}
    if(Defense){Section(Main,TEXT("防御参数"));const double Base=Number(Defense,TEXT("base")),Per=Number(Defense,TEXT("perEnhance"));const auto* E=Model?Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;Row(Main,TEXT("防御力"),N(E?E->Defense(I):Base+Enhance*Per));Row(Main,TEXT("防御基础"),N(Base));Row(Main,TEXT("每级强化防御"),N(Per));
        if(Defense->HasField(TEXT("damageReduction")))Row(Main,TEXT("防御减伤"),N(Number(Defense,TEXT("damageReduction"))*100)+TEXT("%"));if(Defense->HasField(TEXT("staminaCost")))Row(Main,TEXT("防御受击体力"),N(Number(Defense,TEXT("staminaCost"))));}
    const J Bonuses=Object(O,TEXT("bonusStats"));if(Bonuses&&!Bonuses->Values.IsEmpty()){
        Section(Main,TEXT("属性加成"));const TMap<FString,FString> Names={{TEXT("str"),TEXT("力量")},{TEXT("dex"),TEXT("敏捷")},{TEXT("int"),TEXT("智力")},{TEXT("con"),TEXT("体质")},{TEXT("wis"),TEXT("精神")},{TEXT("luck"),TEXT("幸运")},{TEXT("atk"),TEXT("物理攻击")},{TEXT("matk"),TEXT("魔法攻击")},{TEXT("crit"),TEXT("暴击率")},{TEXT("maxHp"),TEXT("最大生命")},{TEXT("maxMp"),TEXT("最大魔法")}};
        for(const auto& P:Bonuses->Values){FString Key(*P.Key);if(const auto* Label=Names.Find(Key))Delta(Main,*Label,P.Value->AsNumber(),Key==TEXT("crit")?TEXT("%"):TEXT(""));}}
    if(O->HasField(TEXT("armorSet"))){Section(Main,TEXT("套装效果"));FString Bonus=String(O,TEXT("setBonusDesc"));if(Bonus.IsEmpty())Bonus=String(Object(O,TEXT("setBonuses")),*String(O,TEXT("armorSet")));Row(Main,TEXT("效果"),Bonus);}
    if(auto Special=Object(O,TEXT("specialAttack"))){Section(Main,TEXT("特殊攻击"));Row(Main,TEXT("伤害类型"),String(Special,TEXT("damageType")));Row(Main,TEXT("伤害公式"),String(Special,TEXT("damageFormula")));for(const auto& F:TArray<TPair<FString,FString>>{{TEXT("duration"),TEXT("持续时间")},{TEXT("cooldown"),TEXT("冷却时间")}})if(Special->HasField(F.Key))Row(Main,F.Value,N(Number(Special,*F.Key))+TEXT("秒"));}
    if(Cat==TEXT("consumable")){const auto Effect=Object(O,TEXT("useEffect"));if(Effect&&!Effect->Values.IsEmpty()){
        Section(Main,TEXT("使用效果"));if(Effect->HasField(TEXT("hp")))Row(Main,TEXT("恢复生命"),Signed(Number(Effect,TEXT("hp"))),1);if(Effect->HasField(TEXT("mp")))Row(Main,TEXT("恢复魔法"),Signed(Number(Effect,TEXT("mp"))),1);
        if(Effect->HasField(TEXT("maxHpPercent")))Row(Main,TEXT("恢复最大生命"),Signed(Number(Effect,TEXT("maxHpPercent")),TEXT("%")),1);if(Effect->HasField(TEXT("maxMpPercent")))Row(Main,TEXT("恢复最大魔法"),Signed(Number(Effect,TEXT("maxMpPercent")),TEXT("%")),1);}
        if(Number(O,TEXT("useCooldown"))>0)Row(Main,TEXT("冷却时间"),N(Number(O,TEXT("useCooldown")))+TEXT("秒"));Row(Main,TEXT("使用方式"),TEXT("双击 / Enter / 拖入快捷栏"));}
    if(I.Count>1)Row(Main,TEXT("堆叠数量"),FString::Printf(TEXT("%lld / %lld"),I.Count,I.StackMax));
    if(I.Place==4)Row(Main,TEXT("取出方式"),TEXT("右键 / 双击 / Enter / 拖入背包"));
    CompleteColdSteelTooltipSummary(I,Model,G,Out);
    return Out;
}
