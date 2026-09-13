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
}
void UColdSteelHUDWidget::NativeDestruct()
{
    if (StatusModel) StatusModel->OnChanged.Remove(StatusModelHandle);
    StatusModelHandle.Reset();
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
    AddCharacterRow(State, TEXT("体力"), TEXT("stamina"), TEXT("当前冲刺与滑铲不消耗体力。破折号表示暂无独立体力数值。"))->AddMeter(FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("A1A44F"))), Scale);
    ExperienceBar = AddCharacterRow(State, TEXT("经验"), TEXT("exp"), TEXT("升级经验 = (20 + 等级×20 + 等级²×12)×8；每级 3 点，余下经验保留。"))->AddMeter(ColdSteelUI::Warning, Scale);

    auto* Attributes = AddCharacterCard(Content, TEXT("基础属性"));
    auto* Grid = WidgetTree->ConstructWidget<UUniformGridPanel>(); Grid->SetSlotPadding(FMargin(ReferenceUnits(4), ReferenceUnits(2))); Attributes->AddChildToVerticalBox(Grid);
    const TCHAR* Labels[] = {TEXT("力量"), TEXT("敏捷"), TEXT("智力"), TEXT("体质"), TEXT("精神"), TEXT("幸运")};
    const TCHAR* Keys[] = {TEXT("str"), TEXT("dex"), TEXT("intt"), TEXT("con"), TEXT("wis"), TEXT("luck")};
    const TCHAR* Details[] = {
        TEXT("基础物攻 = 四舍五入(10 + 力量×0.05 + 敏捷×0.10)\n物防 = 向下取整(体质×1.2 + 力量×0.3)"),
        TEXT("攻速倍率 = 1 + 敏捷×0.02\n体力恢复倍率 = 1 + 敏捷×0.01"),
        TEXT("魔攻 = 向下取整(智力×1.5 + 精神×0.5)\n理论魔法上限 = 100 + 精神×10 + 智力×5"),
        TEXT("理论生命上限 = 100 + 体质×10\n物防 = 向下取整(体质×1.2 + 力量×0.3)\n暴击抵抗 = 体质%"),
        TEXT("魔防 = 向下取整(精神×1.2 + 智力×0.3)\n理论魔法上限 = 100 + 精神×10 + 智力×5"),
        TEXT("幸运不提供随机暴击概率。要害命中由实际命中部位判定。")};
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
    AddCharacterRow(Combat, TEXT("暴击条件"), TEXT("crit"), TEXT("命中敌人要害时由伤害接收方判定；无随机暴击。"));
    AddCharacterRow(Combat, TEXT("暴击抵抗"), TEXT("critRes"), TEXT("基础抵抗 = 体质%。"));
    AddCharacterRow(Combat, TEXT("攻速倍率"), TEXT("aspd"), TEXT("攻速倍率 = 1 + 敏捷×0.02；实际射击间隔 = 基础间隔 / 倍率。"));
    AddCharacterRow(Combat, TEXT("移动速度"), TEXT("moveSpeed"), TEXT("当前姿态下的最大移动速度；随瞄准、蹲伏及冲刺变化。单位：米/秒。"));

    auto* Weapon = AddCharacterCard(Content, TEXT("当前武器实值"));
    AddCharacterRow(Weapon, TEXT("武器"), TEXT("weapon"), TEXT("当前角色使用的实际第一人称武器。"));
    AddCharacterRow(Weapon, TEXT("单发伤害"), TEXT("damage"), TEXT("当前武器的单发基础伤害；最终伤害还受命中部位与目标影响。"));
    AddCharacterRow(Weapon, TEXT("射击间隔"), TEXT("fireInterval"), TEXT("实际武器两次射击的最小时间间隔。"));
    AddCharacterRow(Weapon, TEXT("换弹时间"), TEXT("reload"), TEXT("非空弹匣的实际换弹时间。"));
    AddCharacterRow(Weapon, TEXT("空仓换弹"), TEXT("emptyReload"), TEXT("弹匣为空时的实际换弹时间。"));
    AddCharacterRow(Weapon, TEXT("瞄准时间"), TEXT("ads"), TEXT("进入瞄准状态的实际耗时。耗时越低，瞄准越快。"));
    AddCharacterRow(Weapon, TEXT("弹药"), TEXT("ammo"), TEXT("弹匣剩余 / 备用弹药；射击与换弹后更新。"));

    auto* Detail = AddCharacterCard(Content, TEXT("详细信息"));
    AddCharacterRow(Detail, TEXT("体力恢复"), TEXT("staminaRegen"), TEXT("原项目基础倍率 = 1 + 敏捷×0.01。当前角色尚无体力消耗。"));
    AddCharacterRow(Detail, TEXT("生命恢复"), TEXT("hpRegen"), TEXT("当前角色无被动生命恢复。"));
    AddCharacterRow(Detail, TEXT("魔法恢复"), TEXT("mpRegen"), TEXT("当前角色尚无魔法恢复能力。"));
    AddCharacterRow(Detail, TEXT("碰撞体积"), TEXT("collisionRadius"), TEXT("角色胶囊体的当前碰撞半径，单位：米。"));
    AddCharacterRow(Detail, TEXT("移动速度"), TEXT("moveSpeedDetail"), TEXT("当前水平实际速度，单位：米/秒；静止时为零。"));
    AddCharacterRow(Detail, TEXT("闪避冷却"), TEXT("dodgeCooldown"), TEXT("当前角色使用滑铲，没有独立的闪避技能冷却。"));
    AddCharacterRow(Detail, TEXT("攻击距离"), TEXT("attackRange"), TEXT("当前枪械射线检测的最大距离，单位：米。"));
    AddCharacterRow(Detail, TEXT("击退距离"), TEXT("knockback"), TEXT("击退由目标受击逻辑决定，当前无统一角色数值。"));
    AddCharacterRow(Detail, TEXT("视野宽度"), TEXT("viewRange"), TEXT("相机当前水平视角；随瞄准、冲刺与窗口比例变化。"));
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
        for (const auto& Pair : StatusModel->Attributes)
        {
            SetCharacterValue(Pair.Key.ToString(), FString::FromInt(StatusModel->Attribute(Pair.Key)));
            if (auto* Row = CharacterRows.Find(Pair.Key.ToString())) (*Row)->SetCanAllocate(StatusModel->AttributePoints > 0);
        }
        for (const TCHAR* Key : {TEXT("atk"), TEXT("def"), TEXT("matk"), TEXT("mdef")}) SetCharacterValue(Key, FString::Printf(TEXT("%.0f"), StatusModel->Derived(Key)));
        SetCharacterValue(TEXT("critRes"), FString::Printf(TEXT("%.0f%%"), StatusModel->Derived(TEXT("critRes"))));
        for (const TCHAR* Key : {TEXT("aspd"), TEXT("staminaRegen")}) SetCharacterValue(Key, FString::Printf(TEXT("%.2fx"), StatusModel->Derived(Key)));
    }
    SetCharacterValue(TEXT("crit"), TEXT("命中要害"));
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
    if (Character->GetCharacterMovement()) SetCharacterValue(TEXT("moveSpeed"), FString::Printf(TEXT("%.1f m/s"), Character->GetCharacterMovement()->MaxWalkSpeed / 100));
    SetCharacterValue(TEXT("moveSpeedDetail"), FString::Printf(TEXT("%.1f m/s"), Character->GetVelocity().Size2D() / 100));
    const auto* Equipped = StatusModel ? StatusModel->Equipped() : nullptr;
    const FString Weapon = Equipped ? ColdSteelInventory::Text(*Equipped,TEXT("name")) : TEXT("未装备");
    SetCharacterValue(TEXT("weapon"), Weapon);
    if (WeaponNameText) WeaponNameText->SetText(FText::FromString(Weapon));
    SetCharacterValue(TEXT("damage"), FString::Printf(TEXT("%.0f"), ReadFloat(Character, TEXT("DamagePerShot"))));
    const TPair<const TCHAR*, const TCHAR*> Timings[] = {{TEXT("fireInterval"), TEXT("FireInterval")}, {TEXT("reload"), TEXT("ReloadDuration")}, {TEXT("emptyReload"), TEXT("EmptyReloadDuration")}, {TEXT("ads"), TEXT("ADSInDuration")}};
    for (auto Pair : Timings) SetCharacterValue(Pair.Key, FString::Printf(TEXT("%.0f ms"), ReadFloat(Character, Pair.Value) * 1000));
    SetCharacterValue(TEXT("ammo"), FString::Printf(TEXT("%d / %d"), Character->GetMagazineAmmo(), Character->GetReserveAmmo()));
    if (Character->GetCapsuleComponent()) SetCharacterValue(TEXT("collisionRadius"), FString::Printf(TEXT("%.2f m"), Character->GetCapsuleComponent()->GetScaledCapsuleRadius() / 100));
    if (auto* Camera = Character->FindComponentByClass<UCameraComponent>()) SetCharacterValue(TEXT("viewRange"), FString::Printf(TEXT("%.1f°"), Camera->FieldOfView));
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
    StatusTooltipNote->SetText(FText::FromString(bBase ? TEXT("物攻加入枪械伤害；物防抵消伤害（最低 1）；攻速倍率缩短射击间隔。体质、精神影响资源上限。魔法技能尚未迁移。") : TEXT("")));
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
    BuildTopVitals(Root);
    auto* Button = WidgetTree->ConstructWidget<UButton>();
    Button->SetStyle(FButtonStyle().SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint, 8)).SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, 8, ColdSteelUI::Accent)).SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed, 8)));
    Button->SetContent(MakeReferenceText(TEXT("Caps  角色状态"), 14, ColdSteelUI::TextPrimary));
    Button->OnClicked.AddDynamic(this, &ThisClass::HandleStatusTabClicked);
    auto* NavSlot = Root->AddChildToCanvas(Button); NavSlot->SetAnchors(FAnchors(0, .5f)); NavSlot->SetPosition(FVector2D(ReferenceUnits(16), 0)); NavSlot->SetAutoSize(true);
}
void UColdSteelHUDWidget::OpenStatus() { SetInventoryTab(true); SetInventoryOpen(true); }

FReply UColdSteelHUDWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
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
