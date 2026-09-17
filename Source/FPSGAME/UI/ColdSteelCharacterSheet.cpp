#include "ColdSteelHUDWidget.h"
#include "ColdSteelSkillPage.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "ColdSteelDetailRow.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Blueprint/SlateBlueprintLibrary.h"
#include "Camera/CameraComponent.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/CapsuleComponent.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/ProgressBar.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/UniformGridPanel.h"
#include "Components/UniformGridSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/GameInstance.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "UObject/UnrealType.h"
#include "InputCoreTypes.h"

namespace
{
    float ReadFloat(const UObject* Object, const TCHAR* Key, float Fallback = 0)
    {
        const auto* Field = Object ? FindFProperty<FFloatProperty>(Object->GetClass(), Key) : nullptr;
        return Field ? Field->GetPropertyValue_InContainer(Object) : Fallback;
    }
}

void UColdSteelHUDWidget::NativeConstruct()
{
    Super::NativeConstruct();
    StatusModel = GetGameInstance() ? GetGameInstance()->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    if (StatusModel && !StatusModelHandle.IsValid())
        StatusModelHandle = StatusModel->OnChanged.AddUObject(this, &ThisClass::RefreshCharacterSheet);
    RefreshCharacterSheet();
    if(StatusModel&&!StaminaHandle.IsValid())StaminaHandle=StatusModel->OnStaminaChanged.AddUObject(this,&ThisClass::RefreshStamina);
    RefreshStamina();
}
void UColdSteelHUDWidget::NativeDestruct()
{
    CancelQuickDrag();
    if (StatusModel) StatusModel->OnChanged.Remove(StatusModelHandle);
    StatusModelHandle.Reset();
    if(StatusModel)StatusModel->OnStaminaChanged.Remove(StaminaHandle);
    StaminaHandle.Reset();
    if (bInventoryOpen) SetInventoryOpen(false);
    HideStatusTooltip(); HideEquipmentTooltip();
    Super::NativeDestruct();
}

UVerticalBox* UColdSteelHUDWidget::AddCharacterCard(UVerticalBox* Parent, const FString& Title)
{
    auto* Surface = MakeSurface(ColdSteelUI::StatusCard, ReferenceUnits(ColdSteelUI::CardRadius), ColdSteelUI::Border, ReferenceUnits(1));
    Surface->SetPadding(FMargin(ReferenceUnits(14), ReferenceUnits(12)));
    Parent->AddChildToVerticalBox(Surface)->SetPadding(FMargin(ReferenceUnits(12), ReferenceUnits(6)));
    auto* Column = WidgetTree->ConstructWidget<UVerticalBox>(); Surface->SetContent(Column);
    if (!Title.IsEmpty())
    {
        auto* Heading = WidgetTree->ConstructWidget<UHorizontalBox>();
        Column->AddChildToVerticalBox(Heading)->SetPadding(FMargin(0, 0, 0, ReferenceUnits(8)));
        auto* Accent = MakeSurface(ColdSteelUI::Accent, 0, FLinearColor::Transparent, 0);
        auto* AccentSize = WidgetTree->ConstructWidget<USizeBox>();
        AccentSize->SetWidthOverride(ReferenceUnits(3)); AccentSize->SetHeightOverride(ReferenceUnits(16)); Accent->SetContent(AccentSize);
        Heading->AddChildToHorizontalBox(Accent)->SetPadding(FMargin(0, 0, ReferenceUnits(7), 0));
        Heading->AddChildToHorizontalBox(MakeInventoryText(Title, 16, ColdSteelUI::TextPrimary, false, true));
        auto* Divider = MakeSurface(ColdSteelUI::Border, 0, FLinearColor::Transparent, 0);
        auto* DividerSize = WidgetTree->ConstructWidget<USizeBox>(); DividerSize->SetHeightOverride(ReferenceUnits(1)); Divider->SetContent(DividerSize);
        auto* DividerSlot = Heading->AddChildToHorizontalBox(Divider); DividerSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        DividerSlot->SetVerticalAlignment(VAlign_Center); DividerSlot->SetPadding(FMargin(ReferenceUnits(10), 0, 0, 0));
    }
    return Column;
}

UColdSteelDetailRow* UColdSteelHUDWidget::AddCharacterRow(UVerticalBox* Parent, const FString& Label, const FString& Key, const FString& Detail)
{
    auto* Row = CreateWidget<UColdSteelDetailRow>(GetOwningPlayer());
    Row->Configure(Label, ColdSteelUI::PixelScale(this), Key!=TEXT("weapon")&&Key!=TEXT("crit")&&Key!=TEXT("rank"));
    CharacterRows.Add(Key, Row); CharacterTitles.Add(Key, Label); CharacterDetails.Add(Key, Detail);
    Row->ShowDetail.BindWeakLambda(this, [this, Key]() { ShowStatusTooltip(Key); });
    Row->HideDetail.BindWeakLambda(this, [this, Key]() { if (ActiveStatusKey == Key) HideStatusTooltip(); });
    Row->Allocate.BindWeakLambda(this, [this, Key]() { if (StatusModel) StatusModel->AllocateAttribute(*Key); });
    if (Parent) Parent->AddChildToVerticalBox(Row)->SetPadding(FMargin(0, ReferenceUnits(2)));
    return Row;
}

UWidget* UColdSteelHUDWidget::BuildStatusPage()
{
    StatusScroll = WidgetTree->ConstructWidget<UScrollBox>();
    StatusScroll->SetScrollbarThickness(FVector2D(ReferenceUnits(6), ReferenceUnits(6)));
    StatusScroll->SetAllowOverscroll(false);
    StatusScroll->SetConsumeMouseWheel(EConsumeMouseWheel::Always);
    auto* Content = WidgetTree->ConstructWidget<UVerticalBox>(); StatusScroll->AddChild(Content);
    auto* Identity = AddCharacterCard(Content, TEXT(""));
    auto* IdentityRow = WidgetTree->ConstructWidget<UHorizontalBox>(); Identity->AddChildToVerticalBox(IdentityRow);
    auto* IdentityNames=WidgetTree->ConstructWidget<UVerticalBox>();
    auto* NameColumn=IdentityRow->AddChildToHorizontalBox(IdentityNames);NameColumn->SetSize(FSlateChildSize(ESlateSizeRule::Fill));NameColumn->SetVerticalAlignment(VAlign_Center);
    CharacterNameText = MakeInventoryText(TEXT("轮回者"), 20, ColdSteelUI::TextPrimary, false, true);
    CharacterNameText->SetAutoWrapText(true);IdentityNames->AddChildToVerticalBox(CharacterNameText);
    CharacterClassText = MakeInventoryText(TEXT("初心者"), 12, ColdSteelUI::TextSecondary);
    IdentityNames->AddChildToVerticalBox(CharacterClassText)->SetPadding(FMargin(0,ReferenceUnits(4),0,0));
    auto* LevelBadge=MakeSurface(ColdSteelUI::Content,ReferenceUnits(ColdSteelUI::ButtonRadius),ColdSteelUI::Border,ReferenceUnits(1));
    LevelBadge->SetPadding(FMargin(ReferenceUnits(12),ReferenceUnits(8)));
    auto* BadgeSlot=IdentityRow->AddChildToHorizontalBox(LevelBadge);BadgeSlot->SetVerticalAlignment(VAlign_Center);BadgeSlot->SetPadding(FMargin(ReferenceUnits(12),0,0,0));
    auto* LevelColumn=WidgetTree->ConstructWidget<UVerticalBox>();LevelBadge->SetContent(LevelColumn);
    CharacterLevelText = MakeInventoryText(TEXT("Lv.1"), 16, ColdSteelUI::TextPrimary, true, true);
    CharacterLevelText->SetJustification(ETextJustify::Right);LevelColumn->AddChildToVerticalBox(CharacterLevelText);
    AttributePointsText = MakeInventoryText(TEXT("属性点 0"), 12, ColdSteelUI::Accent);
    AttributePointsText->SetJustification(ETextJustify::Right);
    LevelColumn->AddChildToVerticalBox(AttributePointsText)->SetPadding(FMargin(0,ReferenceUnits(4),0,0));

    auto* State = AddCharacterCard(Content, TEXT("状态"));
    const float Scale = ColdSteelUI::PixelScale(this);
    HealthBar = AddCharacterRow(State, TEXT("生命"), TEXT("hp"), TEXT("当前生命 / 当前生命上限。受伤与恢复直接读取角色生命组件。"))->AddMeter(ColdSteelUI::Success, Scale);
    ManaBar = AddCharacterRow(State, TEXT("魔法"), TEXT("mp"), TEXT("当前魔法 / 魔法上限。药水可恢复，随角色保存。"))->AddMeter(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("55799D"))), Scale);
    StaminaSheetBar=AddCharacterRow(State, TEXT("体力"), TEXT("stamina"), TEXT("奔跑、近战攻击、采集与闪避消耗体力；不足时无法开始对应动作。体力上限为 100 + 装备加成，基础敏捷与装备敏捷提高恢复速度。"))->AddMeter(ColdSteelUI::Stamina, Scale);
    ExperienceBar = AddCharacterRow(State, TEXT("经验"), TEXT("exp"), TEXT("升级经验 = (20 + 等级×20 + 等级²×12)×8；每级 3 点，余下经验保留。"))->AddMeter(ColdSteelUI::Warning, Scale);

    auto* Attributes = AddCharacterCard(Content, TEXT("基础属性"));
    auto* Grid = WidgetTree->ConstructWidget<UUniformGridPanel>(); Grid->SetSlotPadding(FMargin(ReferenceUnits(4), ReferenceUnits(2))); Attributes->AddChildToVerticalBox(Grid);
    const TCHAR* Labels[] = {TEXT("力量"), TEXT("敏捷"), TEXT("智力"), TEXT("体质"), TEXT("精神"), TEXT("幸运")};
    const TCHAR* Keys[] = {TEXT("str"), TEXT("dex"), TEXT("intt"), TEXT("con"), TEXT("wis"), TEXT("luck")};
    const TCHAR* Details[] = {
        TEXT("基础物攻 = 四舍五入(10 + 力量×0.05 + 敏捷×0.10)\n物防 = 向下取整(体质×1.2 + 力量×0.3)"),
        TEXT("攻速倍率 = 1 + 敏捷×0.02（只作用于近战，枪械射速取武器基础值）\n体力恢复倍率 = 1 + 敏捷×0.015\n换弹速度 = ×（1 + 敏捷×0.003），与快手、附魔各自相乘"),
        TEXT("魔攻 = 向下取整(智力×1.5 + 精神×0.5)\n理论魔法上限 = 100 + 精神×10 + 智力×5 + (等级-1)×10"),
        TEXT("理论生命上限 = 100 + 体质×10 + (等级-1)×10\n物防 = 向下取整(体质×1.2 + 力量×0.3)\n暴击抵抗 = 体质%"),
        TEXT("魔防 = 向下取整(精神×1.2 + 智力×0.3)\n理论魔法上限 = 100 + 精神×10 + 智力×5 + (等级-1)×10"),
        TEXT("基础暴击率 = 向下取整(2 + 幸运)%\n随机暴击概率 = 暴击率 − 目标暴击抵抗，最低为零。武器与火球均可触发。")};
    for (int32 I = 0; I < 6; ++I)
    {
        auto* Cell = Grid->AddChildToUniformGrid(AddCharacterRow(nullptr, Labels[I], Keys[I], Details[I]), I / 2, I % 2);
        Cell->SetHorizontalAlignment(HAlign_Fill);
    }
    auto* Combat = AddCharacterCard(Content, TEXT("战斗属性"));
    auto* BaseNote = MakeInventoryText(TEXT("角色基础值"), 12, ColdSteelUI::TextTertiary);
    Combat->AddChildToVerticalBox(BaseNote)->SetPadding(FMargin(ReferenceUnits(8), 0, 0, ReferenceUnits(4)));
    AddCharacterRow(Combat, TEXT("物理攻击"), TEXT("atk"), TEXT("基础物攻 = 四舍五入(10 + 力量×0.05 + 敏捷×0.10)。当前枪械伤害单独列于武器实值。"));
    AddCharacterRow(Combat, TEXT("物理防御"), TEXT("def"), TEXT("物防 = 向下取整(体质×1.2 + 力量×0.3)。"));
    AddCharacterRow(Combat, TEXT("魔法攻击"), TEXT("matk"), TEXT("魔攻 = 向下取整(智力×1.5 + 精神×0.5)。"));
    AddCharacterRow(Combat, TEXT("魔法防御"), TEXT("mdef"), TEXT("魔防 = 向下取整(精神×1.2 + 智力×0.3)。"));
    AddCharacterRow(Combat, TEXT("暴击率"), TEXT("crit"), TEXT("基础暴击率 = 向下取整(2 + 幸运)。随机暴击率 = max(0, 暴击率 - 目标抗暴)。头部要害仍可触发一次暴击。"));
    AddCharacterRow(Combat, TEXT("暴击倍率"), TEXT("critMultiplier"), TEXT("技能倍率 = 1 + 50% + 技能等级 × 5%；步枪精通的要害倍率另行相乘。"));
    AddCharacterRow(Combat, TEXT("暴击抵抗"), TEXT("critRes"), TEXT("基础抵抗 = 体质%。"));
    AddCharacterRow(Combat, TEXT("攻速倍率"), TEXT("aspd"), TEXT("攻速倍率 = 1 + 敏捷×0.02；实际射击间隔 = 基础间隔 / 倍率。"));
    AddCharacterRow(Combat, TEXT("步行速度"), TEXT("moveSpeed"), TEXT("站立、未瞄准时的步行速度上限，读取角色步行配置；不采样实时速度。单位：米/秒。"));
    AddCharacterRow(Combat, TEXT("奔跑速度"), TEXT("moveSpeedDetail"), TEXT("站立冲刺状态的速度上限，读取角色奔跑配置；不包含滑铲、瞄准或过渡状态。单位：米/秒。"));

    auto* Weapon = AddCharacterCard(Content, TEXT("当前武器实值"));
    AddCharacterRow(Weapon, TEXT("武器"), TEXT("weapon"), TEXT("当前角色使用的实际第一人称武器。"));
    AddCharacterRow(Weapon, TEXT("单发伤害"), TEXT("damage"), TEXT("当前武器的单发基础伤害；最终伤害还受命中部位与目标影响。"));
    AddCharacterRow(Weapon, TEXT("射击间隔"), TEXT("fireInterval"), TEXT("实际武器两次射击的最小时间间隔。"));
    AddCharacterRow(Weapon, TEXT("换弹时间"), TEXT("reload"), TEXT("非空弹匣的实际换弹时间。"));
    AddCharacterRow(Weapon, TEXT("空仓换弹"), TEXT("emptyReload"), TEXT("弹匣为空时的实际换弹时间。"));
    AddCharacterRow(Weapon, TEXT("瞄准时间"), TEXT("ads"), TEXT("进入瞄准状态的实际耗时。耗时越低，瞄准越快。"));
    AddCharacterRow(Weapon, TEXT("弹药"), TEXT("ammo"), TEXT("弹匣剩余 / 备用弹药；射击与换弹后更新。"));

    auto* Detail = AddCharacterCard(Content, TEXT("详细信息"));
    AddCharacterRow(Detail, TEXT("体力恢复"), TEXT("staminaRegen"), TEXT("停止消耗后延迟恢复；恢复速度 = 基础恢复 × (1 + 敏捷×0.015)。"));
    AddCharacterRow(Detail, TEXT("生命恢复"), TEXT("hpRegen"), TEXT("每秒恢复 (1 + 祭品固定加成) × 祭品恢复倍率。"));
    AddCharacterRow(Detail, TEXT("魔法恢复"), TEXT("mpRegen"), TEXT("每秒恢复 1 + 精神×0.08 + 智力×0.02，四舍五入保留两位小数；战斗中也恢复。"));
    AddCharacterRow(Detail, TEXT("碰撞体积"), TEXT("collisionRadius"), TEXT("角色胶囊体的当前碰撞半径，单位：米。"));
    AddCharacterRow(Detail, TEXT("闪避冷却"), TEXT("dodgeCooldown"), TEXT("当前角色使用滑铲，没有独立的闪避技能冷却。"));
    AddCharacterRow(Detail, TEXT("攻击距离"), TEXT("attackRange"), TEXT("当前枪械射线检测的最大距离，单位：米。"));
    AddCharacterRow(Detail, TEXT("击退距离"), TEXT("knockback"), TEXT("击退由目标受击逻辑决定，当前无统一角色数值。"));
    AddCharacterRow(Detail, TEXT("常态垂直视角"), TEXT("viewRange"), TEXT("未瞄准、未冲刺时的基础垂直视角配置；不含开镜缩放、冲刺扩张和开火震动，不受窗口宽高比影响。"));
    auto* Loop = AddCharacterCard(Content, TEXT("轮回信息"));
    const TCHAR* LoopLabels[] = {TEXT("轮回次数"), TEXT("存活天数"), TEXT("击杀数"), TEXT("完成任务"), TEXT("基因锁"), TEXT("主神评价")};
    const TCHAR* LoopKeys[] = {TEXT("loopCount"), TEXT("surviveDays"), TEXT("kills"), TEXT("quests"), TEXT("geneLock"), TEXT("rank")};
    for (int32 I = 0; I < 6; ++I) AddCharacterRow(Loop, LoopLabels[I], LoopKeys[I], TEXT("当前没有该项进度记录。"));
    return StatusScroll;
}

void UColdSteelHUDWidget::SetCharacterValue(const FString& Key, const FString& Value, bool bAvailable)
{
    if (auto* Row = CharacterRows.Find(Key)) if (*Row) (*Row)->SetValue(Value, bAvailable);
}
void UColdSteelHUDWidget::RefreshCharacterSheet()
{
    RefreshTopVitals();
    RefreshStamina();
    if (!StatusModel && GetGameInstance()) StatusModel = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (StatusModel)
    {
        if (CharacterNameText) CharacterNameText->SetText(FText::FromString(StatusModel->CharacterName));
        if (CharacterClassText) CharacterClassText->SetText(FText::FromString(StatusModel->CharacterClass));
        if (CharacterLevelText) CharacterLevelText->SetText(FText::FromString(FString::Printf(TEXT("Lv.%d"), StatusModel->Level)));
        if (AttributePointsText) AttributePointsText->SetText(FText::FromString(FString::Printf(TEXT("属性点 %d"), StatusModel->AttributePoints)));
        SetCharacterValue(TEXT("exp"),FString::Printf(TEXT("%lld/%lld"),StatusModel->Experience(),StatusModel->MaxExperience()));
        if(ExperienceBar)ExperienceBar->SetPercent(float(StatusModel->Experience())/StatusModel->MaxExperience());
        SetCharacterValue(TEXT("mp"),FString::Printf(TEXT("%.0f/%.0f"),StatusModel->Mana(),StatusModel->Derived(TEXT("maxMp"))));
        if(ManaBar)ManaBar->SetPercent(StatusModel->Mana()/FMath::Max(1.f,StatusModel->Derived(TEXT("maxMp"))));
        SetCharacterValue(TEXT("kills"),FString::FromInt(StatusModel->Kills()));
        CharacterDetails.Add(TEXT("kills"),TEXT("实际击杀累计，每个敌人死亡只结算一次，随角色保存。"));
        CharacterDetails.Add(TEXT("wis"),FString::Printf(TEXT("精神提升魔法防御、魔法攻击与魔力上限。基础 %d + 步枪精通 %d；技能加成常驻，不占用属性点。"),StatusModel->Attributes.FindRef(TEXT("wis")),StatusModel->RifleEffect().Wisdom));
        CharacterDetails.Add(TEXT("luck"),FString::Printf(TEXT("基础 %d + 暴击技能 %d；暴击率 = 2 + 总幸运，扣除目标体质抗暴后掷随机暴击。要害命中不重复叠加暴击倍率。"),StatusModel->Attributes.FindRef(TEXT("luck")),StatusModel->CriticalStrikeEffect().Luck));
        SetCharacterValue(TEXT("critMultiplier"),FString::Printf(TEXT("%.2fx"),1+StatusModel->CriticalStrikeEffect().CriticalDamageBonus));
        CharacterDetails.Add(TEXT("critMultiplier"),FString::Printf(TEXT("暴击技能提供额外 %.0f%% 伤害；技能倍率 %.2f。随机暴击或要害命中只应用一次；步枪要害倍率仍独立。"),StatusModel->CriticalStrikeEffect().CriticalDamageBonus*100,1+StatusModel->CriticalStrikeEffect().CriticalDamageBonus));
        CharacterDetails.Add(TEXT("dex"),FString::Printf(TEXT("基础 %d + 巧手 %d + 手枪精通 %d；技能加成常驻，不占用属性点。\n近战攻速倍率 = 1 + 总敏捷×0.02（枪械射速取武器基础值，不受敏捷影响）\n体力恢复倍率 = 1 + (基础敏捷+装备敏捷)×0.015\n换弹速度 ×（1 + (基础敏捷+装备敏捷)×0.003），与快手、附魔各自相乘\n巧手额外提供换弹速度 +%.0f%%。"),StatusModel->Attributes.FindRef(TEXT("dex")),StatusModel->DexterousHandsEffect().Dexterity,StatusModel->PistolEffect().Dexterity,StatusModel->DexterousHandsEffect().ReloadSpeed*100));
        const FString MovementDetail=FString::Printf(TEXT("实际持手枪时，基础移动速度 ×（1 + 手枪精通移速加成）。当前倍率 %.2f；收起手枪或改持工具时移除。"),StatusModel->PistolMovementMultiplier());
        CharacterDetails.Add(TEXT("moveSpeed"),MovementDetail);CharacterDetails.Add(TEXT("moveSpeedDetail"),MovementDetail);
        const double DexReloadSpeed=1.+FMath::Max(0.,double(StatusModel->Attribute(TEXT("dex")))+StatusModel->EquipmentBonus(TEXT("dex")))*ColdSteelWeaponStats::DexReloadSpeedPerPoint;
        const FString ReloadDetail=FString::Printf(TEXT("基础耗时 ÷（敏捷 %.2f × 快手 %.2f × 附魔/改造）= 实际换弹时间；普通、空仓换弹均生效，动作与音效同步加速。"),DexReloadSpeed,StatusModel->ReloadSpeedMultiplier());
        CharacterDetails.Add(TEXT("reload"),ReloadDetail);CharacterDetails.Add(TEXT("emptyReload"),ReloadDetail);
        for (const auto& Pair : StatusModel->Attributes)
        {
            SetCharacterValue(Pair.Key.ToString(), FString::FromInt(StatusModel->Attribute(Pair.Key)));
            if (auto* Row = CharacterRows.Find(Pair.Key.ToString())) (*Row)->SetCanAllocate(StatusModel->AttributePoints > 0);
        }
        for (const TCHAR* Key : {TEXT("atk"), TEXT("def"), TEXT("matk"), TEXT("mdef")}) SetCharacterValue(Key, FString::Printf(TEXT("%.0f"), StatusModel->Derived(Key)));
        SetCharacterValue(TEXT("critRes"), FString::Printf(TEXT("%.0f%%"), StatusModel->Derived(TEXT("critRes"))));
        SetCharacterValue(TEXT("aspd"),FString::Printf(TEXT("%.2fx"),StatusModel->Derived(TEXT("aspd"))));
        SetCharacterValue(TEXT("crit"),FString::Printf(TEXT("%.0f%%"),StatusModel->Derived(TEXT("crit"))));
        SetCharacterValue(TEXT("hpRegen"),FString::Printf(TEXT("%.2f/秒"),StatusModel->Derived(TEXT("hpRegen"))));
        SetCharacterValue(TEXT("mpRegen"),FString::Printf(TEXT("%.2f/秒"),StatusModel->Derived(TEXT("mpRegen"))));
        CharacterDetails.Add(TEXT("def"),TEXT("物防 = floor(体质×1.2 + 力量×0.3) + 装备防御。减伤 = floor(伤害×60/(防御+60))，不低于 floor(原伤害×10%)；格挡随后独立计算。"));
        CharacterDetails.Add(TEXT("mdef"),TEXT("魔防 = floor(精神×1.2 + 智力×0.3)。魔法减伤使用同一 60/(魔防+60) 公式与10%下限。"));
        SetCharacterValue(TEXT("staminaRegen"),FString::Printf(TEXT("%.1f/秒"),StatusModel->StaminaRecoveryRate()));
        const auto& T=StatusModel->StaminaSettings();
        CharacterDetails.Add(TEXT("staminaRegen"),FString::Printf(TEXT("停止消耗 %.1f 秒后恢复。基础 %.1f/秒 × 敏捷倍率 %.2f = %.1f/秒。"),T.RecoveryDelay,T.RecoveryPerSecond,StatusModel->Derived(TEXT("staminaRegen")),StatusModel->StaminaRecoveryRate()));
        CharacterDetails.Add(TEXT("stamina"),FString::Printf(TEXT("上限 = %.0f + 装备加成（体质系数 %.0f）。奔跑 %.1f/秒；近战 %.1f/次；采集 %.1f/次；当前闪避 %.2f/次。"),T.BaseMaximum,T.PerConstitution,T.SprintPerSecond,T.MeleeCost,T.HarvestCost,StatusModel->DodgeStaminaCost()));
        CharacterDetails.Add(TEXT("con"),FString::Printf(TEXT("生命上限 = 100 + 体质×10 + (等级-1)×10\n体力上限 = %.0f + 装备加成（体质系数 %.0f）\n物防 = 向下取整(体质×1.2 + 力量×0.3)\n暴击抵抗 = 体质%%"),T.BaseMaximum,T.PerConstitution));
    }
    const auto* Character = GetOwningPlayerPawn<AFPSGAMECharacter>();
    // Clear former-pawn values when possession changes or no compatible pawn exists.
    for (const TCHAR* Key : {TEXT("hp"), TEXT("moveSpeed"), TEXT("moveSpeedDetail"), TEXT("weapon"), TEXT("damage"), TEXT("fireInterval"), TEXT("reload"), TEXT("emptyReload"), TEXT("ads"), TEXT("ammo"), TEXT("collisionRadius"), TEXT("viewRange"), TEXT("attackRange")}) SetCharacterValue(Key, TEXT("—"), false);
    if (HealthBar) HealthBar->SetPercent(0);
    if (!Character) return;
    const auto* Health = Character->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Health && Health->MaxHealth > 0)
    {
        const float Ratio = FMath::Clamp(Health->Health / Health->MaxHealth, 0.f, 1.f);
        if (HealthBar) { HealthBar->SetPercent(Ratio); HealthBar->SetFillColorAndOpacity(Ratio <= .25f ? ColdSteelUI::Danger : Ratio <= .5f ? ColdSteelUI::Warning : ColdSteelUI::Success); }
        SetCharacterValue(TEXT("hp"), FString::Printf(TEXT("%.0f/%.0f"), FMath::Max(0.f, Health->Health), Health->MaxHealth));
    }
    SetCharacterValue(TEXT("moveSpeed"), FString::Printf(TEXT("%.1f m/s"), ReadFloat(Character, TEXT("WalkSpeed")) / 100));
    SetCharacterValue(TEXT("moveSpeedDetail"), FString::Printf(TEXT("%.1f m/s"), ReadFloat(Character, TEXT("SprintSpeed")) / 100));
    const auto* Equipped = StatusModel ? StatusModel->Equipped() : nullptr;
    const FString Weapon = Equipped ? ColdSteelInventory::Text(*Equipped,TEXT("name")) : TEXT("未装备");
    SetCharacterValue(TEXT("weapon"), Weapon);
    if (WeaponNameText) WeaponNameText->SetText(FText::FromString(Weapon));
    SetCharacterValue(TEXT("damage"), FString::Printf(TEXT("%.0f"), ReadFloat(Character, TEXT("DamagePerShot"))));
    const TPair<const TCHAR*, const TCHAR*> Timings[] = {{TEXT("fireInterval"), TEXT("FireInterval")}, {TEXT("reload"), TEXT("ReloadDuration")}, {TEXT("emptyReload"), TEXT("EmptyReloadDuration")}, {TEXT("ads"), TEXT("ADSInDuration")}};
    for (auto Pair : Timings) SetCharacterValue(Pair.Key, FString::Printf(TEXT("%.0f ms"), ReadFloat(Character, Pair.Value) * 1000));
    SetCharacterValue(TEXT("ammo"), FString::Printf(TEXT("%d / %d"), Character->GetMagazineAmmo(), Character->GetReserveAmmo()));
    if (Character->GetCapsuleComponent()) SetCharacterValue(TEXT("collisionRadius"), FString::Printf(TEXT("%.2f m"), Character->GetCapsuleComponent()->GetScaledCapsuleRadius() / 100));
    SetCharacterValue(TEXT("viewRange"), FString::Printf(TEXT("%.1f°"), ReadFloat(Character, TEXT("BaseVerticalFieldOfView"))));
    SetCharacterValue(TEXT("attackRange"), FString::Printf(TEXT("%.0f m"), ReadFloat(Character, TEXT("TraceDistance")) / 100));
    if (!ActiveStatusKey.IsEmpty()) ShowStatusTooltip(ActiveStatusKey);
}

void UColdSteelHUDWidget::ShowStatusTooltip(const FString& InKey)
{
    const FString Key = InKey; // callers may pass ActiveStatusKey itself
    if (!StatusTooltip || !bInventoryOpen || !bStatusTabActive || !CharacterRows.Contains(Key)) return;
    const FString Value = CharacterRows[Key]->GetValue();
    const FString Description = CharacterDetails.FindRef(Key);
    const FString Signature = Key + Value + Description;
    if (StatusTooltip->IsVisible() && StatusDetailSignature == Signature) { UpdateStatusTooltipPlacement(); return; }
    StatusDetailSignature = Signature;
    ActiveStatusKey = Key;
    StatusTooltipTitle->SetText(FText::FromString(CharacterTitles.FindRef(Key)));
    StatusTooltipDescription->SetText(FText::FromString(Description));
    StatusTooltipDescription->SetWrapTextAt(ReferenceUnits(286));
    StatusTooltipRowsBox->ClearChildren();
    auto* CurrentRow=WidgetTree->ConstructWidget<UHorizontalBox>();StatusTooltipRowsBox->AddChildToVerticalBox(CurrentRow);
    auto* CurrentLabel=CurrentRow->AddChildToHorizontalBox(MakeReferenceText(TEXT("当前值"),12,ColdSteelUI::TextSecondary));
    CurrentLabel->SetSize(FSlateChildSize(ESlateSizeRule::Fill));CurrentLabel->SetVerticalAlignment(VAlign_Center);
    auto* CurrentValue=MakeReferenceText(Value,14,ColdSteelUI::TextPrimary,Key!=TEXT("weapon")&&Key!=TEXT("crit")&&Key!=TEXT("rank"),true);
    CurrentValue->SetAutoWrapText(true);CurrentValue->SetJustification(ETextJustify::Right);
    auto* CurrentValueSlot=CurrentRow->AddChildToHorizontalBox(CurrentValue);CurrentValueSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));CurrentValueSlot->SetPadding(FMargin(ReferenceUnits(8),0,0,0));
    const bool bBase = StatusModel && (StatusModel->Attributes.Contains(*Key) || Key == TEXT("atk") || Key == TEXT("def") || Key == TEXT("matk") || Key == TEXT("mdef") || Key == TEXT("critRes") || Key == TEXT("aspd") || Key == TEXT("staminaRegen"));
    StatusTooltipNote->SetText(FText::FromString(bBase ? TEXT("武器按独立属性系数计算伤害；物防和魔防按比例减伤。生命与魔法上限含每级成长，魔法值按秒恢复。") : TEXT("")));
    StatusTooltipNote->SetWrapTextAt(ReferenceUnits(286));
    StatusTooltipNote->SetVisibility(bBase ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
    StatusTooltip->SetVisibility(ESlateVisibility::HitTestInvisible);
    // Signature is stored separately from tooltip metadata to avoid nested stock tooltips.
    StatusTooltip->ForceLayoutPrepass();
    UpdateStatusTooltipPlacement();
}
void UColdSteelHUDWidget::HideStatusTooltip()
{
    ActiveStatusKey.Reset();
    StatusDetailSignature.Reset();
    if (StatusTooltip) StatusTooltip->SetVisibility(ESlateVisibility::Collapsed);
}
void UColdSteelHUDWidget::UpdateStatusTooltipPlacement()
{
    if (!StatusTooltipCanvasSlot || ActiveStatusKey.IsEmpty() || !CharacterRows.Contains(ActiveStatusKey)) return;
    const FVector2D Viewport = UWidgetLayoutLibrary::GetViewportSize(this) / ColdSteelUI::PixelScale(this);
    const float Gap = ReferenceUnits(12);
    FVector2D Extent(FMath::Min(ReferenceUnits(320), Viewport.X - Gap * 2), FMath::Min(StatusTooltip->GetDesiredSize().Y, Viewport.Y - Gap * 2));
    Extent.Y = FMath::Max(ReferenceUnits(120), Extent.Y);
    const auto* Row = CharacterRows[ActiveStatusKey].Get();
    const FGeometry& RowGeometry = Row->GetCachedGeometry();
    FVector2D Position = GetCachedGeometry().AbsoluteToLocal(RowGeometry.LocalToAbsolute(FVector2D::ZeroVector));
    Position.X -= Extent.X + Gap;
    Position.Y += ReferenceUnits(6);
    Position.X = FMath::Clamp(Position.X, Gap, FMath::Max(Gap, Viewport.X - Extent.X - Gap));
    Position.Y = FMath::Clamp(Position.Y, Gap, FMath::Max(Gap, Viewport.Y - Extent.Y - Gap));
    StatusTooltipCanvasSlot->SetAnchors(FAnchors(0));
    StatusTooltipCanvasSlot->SetPosition(Position); StatusTooltipCanvasSlot->SetSize(Extent);
}

void UColdSteelHUDWidget::BuildCharacterSummary(UCanvasPanel* Root)
{
    // The left-edge "Caps 角色状态" entry is removed on request; Caps still opens the character sheet
    // through HandlePanelShortcut, and the right rail keeps its 人物状态 entry while the drawer is out.
    BuildTopVitals(Root);
}
void UColdSteelHUDWidget::OpenStatus() { SetInventoryTab(true); SetInventoryOpen(true); }

FReply UColdSteelHUDWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if(IsQuickDragging()&&Event.GetKey()==EKeys::Escape){CancelQuickDrag();return FReply::Handled();}
    if (HandlePanelShortcut(Event.GetKey(), Event.IsRepeat())) return FReply::Handled();
    if(Event.GetKey()==EKeys::Escape && (bTimelineDetailsOpen || TimelineDetailMotion>0)){SetTimelineDetailsOpen(false);return FReply::Handled();}
    if(Event.GetKey()==EKeys::Escape&&HasPinnedItemTooltip()){HideItemTooltip(true);return FReply::Handled();}
    if(bInventoryOpen&&Event.GetKey()==EKeys::G&&StatusModel){StatusModel->CycleWeapon();return FReply::Handled();}
    if (bInventoryOpen && Event.GetKey() == EKeys::Escape)
    {
        if(Event.GetKey()==EKeys::Escape&&UWidgetBlueprintLibrary::IsDragDropping()){UWidgetBlueprintLibrary::CancelDragDrop();return FReply::Handled();}
        if(WarehouseDetails&&Event.GetKey()==EKeys::Escape){HideWarehouseDetails();return FReply::Handled();}
        if(bWarehouseOpen&&Event.GetKey()==EKeys::Escape){CloseWarehouse();return FReply::Handled();}
        if(bSkillsTabActive && SkillPage && SkillPage->GoBack())return FReply::Handled();
        SetInventoryOpen(false);
        return FReply::Handled();
    }
    return Super::NativeOnPreviewKeyDown(Geometry, Event);
}
