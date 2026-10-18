#include "ColdSteelConsumablePresentation.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelStatusModel.h"
#include "../Items/FoodSpoilage.h"
#include "../Survival/FPSSurvivalTypes.h"
#include "Dom/JsonObject.h"

namespace
{
    double Num(const FJsonObject* O,const TCHAR* Key,double Default=0)
    {
        double V=Default;
        return O&&O->TryGetNumberField(Key,V)?V:Default;
    }
    bool Has(const FJsonObject* O,const TCHAR* Key){return O&&O->HasField(Key);}
    const FJsonObject* Obj(const FJsonObject* O,const TCHAR* Key)
    {
        const TSharedPtr<FJsonObject>* V=nullptr;
        return O&&O->TryGetObjectField(Key,V)&&*V?V->Get():nullptr;
    }
    FString Str(const FJsonObject* O,const TCHAR* Key,const FString& Default=TEXT(""))
    {
        FString V;
        return O&&O->TryGetStringField(Key,V)?V:Default;
    }
    FString N(double V)
    {
        FString S=FString::Printf(TEXT("%.2f"),V);
        while(S.EndsWith(TEXT("0")))S.LeftChopInline(1);
        if(S.EndsWith(TEXT(".")))S.LeftChopInline(1);
        return S==TEXT("-0")?TEXT("0"):S;
    }
    FString Signed(double V,const TCHAR* Unit=TEXT(""))
    {
        return (V>0?TEXT("+"):TEXT(""))+N(V)+Unit;
    }
    int32 SignTone(double V){return V>0?1:V<0?-1:0;}

    /** 固定值 + 上限百分比合并成一行，例如「+30 + 15%上限」。 */
    FString Combined(double Flat,double Percent)
    {
        if(Flat>0&&Percent>0)return Signed(Flat)+TEXT(" + ")+N(Percent)+TEXT("%上限");
        if(Percent>0)return Signed(Percent,TEXT("%上限"));
        if(Flat>0)return Signed(Flat);
        return FString();
    }

    enum class EKind : uint8 {Food,Drink,Potion,Raw};
    EKind KindOf(const FColdSteelItem& Item,const FJsonObject* Data)
    {
        const FString& D=Item.Definition;
        if(D==TEXT("hp_potion")||D.StartsWith(TEXT("hp_potion_"))||
            D==TEXT("mp_potion")||D.StartsWith(TEXT("mp_potion_")))return EKind::Potion;
        const FJsonObject* E=Obj(Data,TEXT("useEffect"));
        const bool bFood=E&&(Has(E,TEXT("hunger"))||Has(E,TEXT("maxHungerPercent")));
        if(bFood)return EKind::Food;
        if(!E&&Num(Data,TEXT("spoilDays"))>0)return EKind::Raw;
        return EKind::Drink;
    }

    /** 持续增益：优先读目录 buffs；旧条目退回机制常量，数值必须一致。 */
    void AppendBuffs(const FColdSteelItem& Item,const FJsonObject* Data,TArray<ColdSteelConsumable::FRow>& Out)
    {
        double Duration=0;
        bool bFromData=false;
        TArray<FString> Notes;
        const TArray<TSharedPtr<FJsonValue>>* List=nullptr;
        if(Data&&Data->TryGetArrayField(TEXT("buffs"),List)&&List)
            for(const auto& V:*List)
            {
                const TSharedPtr<FJsonObject> B=V->AsObject();
                if(!B)continue;
                const FString Label=Str(B.Get(),TEXT("label"));
                const double Value=Num(B.Get(),TEXT("value"));
                const FString Unit=Str(B.Get(),TEXT("unit"));
                if(Label.IsEmpty()||FMath::IsNearlyZero(Value))continue;
                Out.Add({Label,Signed(Value,*Unit),TEXT(""),SignTone(Value),false});
                Duration=FMath::Max(Duration,Num(B.Get(),TEXT("duration")));
                const FString Note=Str(B.Get(),TEXT("note"));
                if(!Note.IsEmpty()&&!Notes.Contains(Note))Notes.Add(Note);
                bFromData=true;
            }
        if(!bFromData)
        {
            if(Item.Definition==TEXT("roasted_sausage"))
            {
                Out.Add({TEXT("体力恢复速度"),Signed((FFPSSurvivalState::SausageRecoveryRateMultiplier-1.f)*100.f,TEXT("%")),TEXT(""),1,false});
                Duration=FFPSSurvivalState::SausageRecoveryDuration;
                Notes.Add(TEXT("饱腹已满也可食用；重复食用只刷新持续时间，倍率不叠加。"));
            }
            else if(Item.Definition==TEXT("roasted_large_lamb"))
            {
                Out.Add({TEXT("体力上限"),Signed((FFPSSurvivalState::LargeLambMaximumMultiplier-1.f)*100.f,TEXT("%")),TEXT(""),1,false});
                Out.Add({TEXT("体力恢复速度"),Signed((FFPSSurvivalState::LargeLambRecoveryMultiplier-1.f)*100.f,TEXT("%")),TEXT(""),1,false});
                Duration=FFPSSurvivalState::LargeLambMealDuration;
                Notes.Add(TEXT("提高上限不直接补充体力；饱腹已满也可食用；重复食用只刷新持续时间。"));
            }
        }
        if(Duration>0)Out.Add({TEXT("增益持续"),N(Duration)+TEXT("秒"),TEXT(""),0,false});
        for(const FString& Note:Notes)Out.Add({TEXT(""),Note,TEXT(""),0,false});
    }

    bool Freshness(const FColdSteelItem& Item,UColdSteelStatusModel* Model,FString& Value,int32& Tone)
    {
        const double Lifetime=ColdSteelFood::LifetimeDays(Item);
        if(Lifetime<=0)return false;
        const double Remaining=Model?Model->FoodRemainingDays(Item):Lifetime;
        ColdSteelConsumable::FormatFreshness(Remaining,Lifetime,Value,Tone);
        return true;
    }
}

void ColdSteelConsumable::FormatFreshness(double Remaining,double Lifetime,FString& Value,int32& Tone)
{
    const double Ratio=Lifetime>0?FMath::Clamp(Remaining/Lifetime,0.,1.):0.;
    if(Remaining<=0){Value=TEXT("已腐败");Tone=-1;}
    else
    {
        Value=FString::Printf(TEXT("剩余 %s 天 / 共 %s 天"),*N(Remaining),*N(Lifetime));
        Tone=Ratio>=.5?1:(Ratio>=.2?0:-1);
    }
}

bool ColdSteelConsumable::IsConsumable(const FJsonObject* Data)
{
    if(!Data)return false;
    if(Str(Data,TEXT("category"))==TEXT("consumable"))return true;
    // 生肉/生香肠等可腐败食材：category 仍是 material，但需要新鲜度与烹饪提示。
    return Num(Data,TEXT("spoilDays"))>0;
}

FString ColdSteelConsumable::ValueScope(const FColdSteelItem& Item,const FJsonObject* Data)
{
    switch(KindOf(Item,Data))
    {
    case EKind::Potion:return TEXT("固定值与上限百分比同时结算；数值按当前最大生命／魔法计算。");
    case EKind::Food:return TEXT("饱腹百分比按最大饱腹结算；新鲜度按自然游戏日推进，腐败后不可食用。");
    case EKind::Drink:return TEXT("水分按当前上限结算；多口饮品按剩余次数逐次结算。");
    default:return TEXT("生食材不可直接食用；腐败后转化为腐败食物。");
    }
}

void ColdSteelConsumable::BuildDetailRows(const FColdSteelItem& Item,UColdSteelStatusModel* Model,const FJsonObject* Data,TArray<FRow>& Out)
{
    Out.Reset();
    const EKind Kind=KindOf(Item,Data);
    const FJsonObject* Effect=Obj(Data,TEXT("useEffect"));
    if(Effect)
    {
        TArray<FRow> Use;
        const FString HP=Combined(Num(Effect,TEXT("hp")),Num(Effect,TEXT("maxHpPercent")));
        const FString MP=Combined(Num(Effect,TEXT("mp")),Num(Effect,TEXT("maxMpPercent")));
        const FString Food=Combined(Num(Effect,TEXT("hunger")),Num(Effect,TEXT("maxHungerPercent")));
        if(!HP.IsEmpty())Use.Add({TEXT("恢复生命"),HP,TEXT(""),1,false});
        if(!MP.IsEmpty())Use.Add({TEXT("恢复魔法"),MP,TEXT(""),1,false});
        if(!Food.IsEmpty())Use.Add({TEXT("恢复饱腹"),Food,TEXT(""),1,false});
        if(Has(Effect,TEXT("hydration")))
        {
            const double Water=Num(Effect,TEXT("hydration"));
            Use.Add({Water<0?TEXT("消耗水分"):TEXT("恢复水分"),Signed(Water),TEXT(""),Water<0?-1:1,false});
        }
        if(Has(Effect,TEXT("sanity")))
        {
            const double Sanity=Num(Effect,TEXT("sanity"));
            Use.Add({Sanity<0?TEXT("消耗 SAN"):TEXT("恢复 SAN"),Signed(Sanity),TEXT(""),SignTone(Sanity),false});
        }
        if(!Use.IsEmpty())
        {
            Out.Add({TEXT("使用效果"),TEXT(""),TEXT(""),0,true});
            Out.Append(MoveTemp(Use));
        }
    }

    TArray<FRow> Buffs;
    AppendBuffs(Item,Data,Buffs);
    if(!Buffs.IsEmpty())
    {
        Out.Add({TEXT("持续增益"),TEXT(""),TEXT(""),0,true});
        Out.Append(MoveTemp(Buffs));
    }

    FString FreshValue;
    int32 FreshTone=0;
    if(Freshness(Item,Model,FreshValue,FreshTone))
    {
        Out.Add({TEXT("新鲜度"),TEXT(""),TEXT(""),0,true});
        Out.Add({TEXT("新鲜度"),FreshValue,TEXT(""),FreshTone,false});
        Out.Add({TEXT(""),Kind==EKind::Raw?TEXT("不可直接食用，需投入有燃料的篝火烤熟。"):TEXT("腐败后不可食用，会转化为腐败食物。"),TEXT(""),0,false});
    }

    if(Kind==EKind::Raw)
    {
        // 生食材没有使用动作：只标注用途，简略浮窗也能取到这一行。
        Out.Add({TEXT("用途"),TEXT("烹饪食材"),TEXT(""),0,false});
        Out.Add({TEXT(""),TEXT("烤熟后按成品食物结算饱腹与增益。"),TEXT(""),0,false});
        return;
    }

    TArray<FRow> UseRows;
    const double Duration=Num(Data,TEXT("useDuration"));
    if(Duration>0)UseRows.Add({TEXT("使用时长"),N(Duration)+TEXT("秒"),TEXT(""),0,false});
    const double Cooldown=Num(Data,TEXT("useCooldown"));
    if(Cooldown>0)UseRows.Add({TEXT("冷却时间"),N(Cooldown)+TEXT("秒"),TEXT(""),0,false});
    const int32 MaxUses=FMath::Max(1,int32(Num(Data,TEXT("maxUses"),1)));
    if(MaxUses>1)
    {
        const int32 Remaining=FMath::Clamp(int32(Num(Data,TEXT("remainingUses"),MaxUses)),1,MaxUses);
        UseRows.Add({TEXT("剩余次数"),FString::Printf(TEXT("%d / %d"),Remaining,MaxUses),TEXT(""),0,false});
        if(Item.Definition==TEXT("mineral_water"))
            UseRows.Add({TEXT("瓶内水量"),Remaining>=MaxUses?TEXT("满瓶"):TEXT("半瓶"),TEXT(""),0,false});
    }
    else UseRows.Add({TEXT("使用次数"),TEXT("单次使用"),TEXT(""),0,false});
    if(!UseRows.IsEmpty())
    {
        Out.Add({TEXT("使用"),TEXT(""),TEXT(""),0,true});
        Out.Append(MoveTemp(UseRows));
        Out.Add({TEXT(""),TEXT("右键 / 双击 / Enter / 快捷栏"),TEXT(""),0,false});
    }
}

void ColdSteelConsumable::BuildSummaryRows(const FColdSteelItem& Item,UColdSteelStatusModel* Model,const FJsonObject* Data,TArray<FRow>& Out,int32 MaxRows)
{
    Out.Reset();
    TArray<FRow> Detail;
    BuildDetailRows(Item,Model,Data,Detail);
    auto Find=[&Detail](const TCHAR* Label)->const FRow*
    {
        for(const FRow& R:Detail)if(!R.bSection&&R.Label==Label)return &R;
        return nullptr;
    };
    auto Push=[&](const TCHAR* Label)
    {
        if(Out.Num()>=MaxRows)return;
        if(const FRow* R=Find(Label))Out.Add(*R);
    };

    switch(KindOf(Item,Data))
    {
    case EKind::Potion:
        Push(TEXT("恢复生命"));Push(TEXT("恢复魔法"));Push(TEXT("冷却时间"));Push(TEXT("剩余次数"));Push(TEXT("使用次数"));
        break;
    case EKind::Food:
        Push(TEXT("恢复饱腹"));Push(TEXT("恢复水分"));Push(TEXT("消耗水分"));
        Push(TEXT("体力上限"));Push(TEXT("体力恢复速度"));Push(TEXT("新鲜度"));
        break;
    case EKind::Drink:
        Push(TEXT("恢复水分"));Push(TEXT("恢复 SAN"));Push(TEXT("消耗 SAN"));Push(TEXT("剩余次数"));Push(TEXT("使用时长"));
        break;
    default:
        Push(TEXT("新鲜度"));Push(TEXT("用途"));
        break;
    }
    if(Out.IsEmpty())
        for(const FRow& R:Detail)
            if(!R.bSection&&!R.Label.IsEmpty()&&Out.Num()<MaxRows)Out.Add(R);
}
