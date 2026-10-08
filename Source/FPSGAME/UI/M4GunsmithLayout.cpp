#include "../Weapons/GunsmithModificationTier.h"
#include "M4GunsmithWidget.h"
#include "SM4PreviewSurface.h"
#include "SMeleePartIcon.h"
#include "SAttachmentSelectionPulse.h"
#include "SFramedAttachmentIcon.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/RSH12OpticAssets.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Production/ProductionToolEnhance.h"
#include "../FPSGAMEPlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Colors/SSimpleGradient.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Styling/CoreStyle.h"

namespace
{
TSharedRef<STextBlock> Label(const FString& Text,int32 Size=14,FLinearColor Color=GunsmithUI::Text,bool Medium=false)
{return SNew(STextBlock).Text(FText::FromString(Text)).Font(GunsmithUI::TextFont(Size,Medium)).ColorAndOpacity(Color).AutoWrapText(true);}
}

TSharedRef<SWidget> UM4GunsmithWidget::GlassPanel(TSharedRef<SWidget> Content,FMargin PanelPadding)
{
    auto Blur=SNew(SBackgroundBlur).BlurStrength(5.f).BlurRadius(13).Padding(0)
        .CornerRadius(FVector4(10,10,10,10)).LowQualityFallbackBrush(&GlassFallback)
        [SNew(SBorder).BorderImage(&PanelBrush).Padding(PanelPadding)[Content]];
    GlassLayers.Add(Blur);
    return SNew(SOverlay)+SOverlay::Slot()[Blur]
        +SOverlay::Slot().VAlign(VAlign_Top).Padding(12,0)
        [SNew(SBox).HeightOverride(1)[SNew(SImage).Image(FCoreStyle::Get().GetBrush("WhiteBrush"))
            .ColorAndOpacity(GunsmithUI::Gray(255,42)).Visibility(EVisibility::HitTestInvisible)]];
}

void UM4GunsmithWidget::LoadCategoryIcons()
{
    CategoryBrushes.Reset();CategoryTextures.Reset();CategoryMaterials.Reset();
    auto* IconMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/ColdGlass/M_CategoryIcon.M_CategoryIcon"));
    auto IconKeys=Model()->Slots(Model()->Definition());
    if(IsToolWorkbench())IconKeys.AddUnique(TEXT("enhance"));
    for(const auto& Key:IconKeys)
    {
        if(Key!=TEXT("enhance")&&!IsCategoryAvailable(Key))continue;
        FString IconDirectory=FPaths::ProjectContentDir()/TEXT("ColdSteelData/AttachmentIcons20260913");
        const FString FramedDirectory=IconDirectory/(IsBowWorkbench()?TEXT("FramedBows"):TEXT("FramedFirearms"));
        const FString SharedFramedPath=FramedDirectory/(TEXT("category_")+Key+TEXT(".png"));
        const bool SharedFirearmCategory=!IsStandaloneWorkbench()&&FPaths::FileExists(SharedFramedPath);
        if(SharedFirearmCategory||((!IsStandaloneWorkbench()||IsBowWorkbench())&&(FPaths::FileExists(FramedDirectory/(Model()->Definition()+TEXT("_category_")+Key+TEXT(".png")))
            ||(!FPaths::FileExists(IconDirectory/(Model()->Definition()+TEXT("_category_")+Key+TEXT(".png")))
                &&FPaths::FileExists(SharedFramedPath)))))IconDirectory=FramedDirectory;
        const FString WeaponIconPath=IconDirectory/(Model()->Definition()+TEXT("_category_")+Key+TEXT(".png"));
        // 近战新改造件允许缺武器专属图：回退通用分类图/SMeleePartIcon，不再整卡隐藏。
        const FString IconPath=SharedFirearmCategory?SharedFramedPath:FPaths::FileExists(WeaponIconPath)?WeaponIconPath:IconDirectory/(TEXT("category_")+Key+TEXT(".png"));
        if(auto* Texture=FImageUtils::ImportFileAsTexture2D(IconPath))
        {
            CategoryTextures.Add(Texture);
            auto Brush=MakeShared<FSlateBrush>();Brush->ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());
            Brush->DrawAs=ESlateBrushDrawType::Image;Brush->SetResourceObject(Texture);
            CategoryBrushes.Add(Key,Brush);
            continue;
        }
        const FString Asset=TEXT("/Game/UI/GunsmithWorkbench/ColdGlass/T_Category_")+Key;
        auto* Texture=LoadObject<UTexture2D>(nullptr,*(Asset+TEXT(".T_Category_")+Key));
        if(!Texture)continue;
        CategoryTextures.Add(Texture);
        auto Brush=MakeShared<FSlateBrush>();Brush->ImageSize=FVector2D(48,48);Brush->DrawAs=ESlateBrushDrawType::Image;
        if(IconMaterial)
        {
            auto* Material=UMaterialInstanceDynamic::Create(IconMaterial,this);
            Material->SetTextureParameterValue(TEXT("IconTexture"),Texture);CategoryMaterials.Add(Material);Brush->SetResourceObject(Material);
        }
        else Brush->SetResourceObject(Texture);
        CategoryBrushes.Add(Key,Brush);
    }
}

FString UM4GunsmithWidget::CategoryPartName(const FString& Key) const
{
    const auto* W=Model()->ModifiableWeapon(Model()->Definition());
    if(!W||!W->Allowed.Contains(Key))return TEXT("待扩展");
    const FString Id=Model()->Draft().FindRef(Key);
    if(const auto* O=Model()->Option(Model()->Definition(),Key,Id.IsEmpty()?TEXT("false"):Id))return O->Name;
    return TEXT("原厂配置");
}

TSharedRef<SWidget> UM4GunsmithWidget::BuildWorkbench()
{
    using namespace GunsmithUI;
    OptionsSignature.Reset();OptionsCategory.Reset();InspectedOptionKey.Reset();OptionCards.Reset();CategoryButtons.Reset();GlassLayers.Reset();LayoutMode=-1;
    EnhanceSignature.Reset();PreviewEnhanceLevel=-1;
    PanelBrush=ColdSteelUI::RoundedBrush(Glass,10,Edge);
    GlassFallback=ColdSteelUI::RoundedBrush(Gray(29),10,Edge);
    RowBrush=ColdSteelUI::RoundedBrush(Row,0,Gray(220,12),.5f);
    OptionFrameBrush=ColdSteelUI::RoundedBrush(FLinearColor::White,8,FLinearColor::Transparent,0);
    NormalButton=FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("Button");
    NormalButton.SetNormal(ColdSteelUI::RoundedBrush(Gray(43,180),7,Gray(215,26)));
    NormalButton.SetHovered(ColdSteelUI::RoundedBrush(Gray(65,220),7,Gray(240,100)));
    NormalButton.SetPressed(ColdSteelUI::RoundedBrush(Gray(24,235),7,Gray(240,110)));
    NormalButton.SetDisabled(ColdSteelUI::RoundedBrush(Gray(24,90),7,Gray(180,12)));
    SelectedButton=NormalButton;SelectedButton.SetNormal(ColdSteelUI::RoundedBrush(Gray(65,200),7,Gray(227,160)));
    // The workbench's SDPIScaler already cancels viewport DPI for this subtree.
    ExclusiveButton=NormalButton;
    ExclusiveButton.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ExclusiveCard,7,ColdSteelUI::ExclusiveBorder,1));
    ExclusiveButton.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ExclusiveCardHover,7,ColdSteelUI::ExclusiveText,1));
    ExclusiveButton.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ExclusiveCardPressed,7,ColdSteelUI::ExclusiveBorder,1));
    LegendaryButton=NormalButton;
    LegendaryButton.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::LegendaryCard,7,ColdSteelUI::LegendaryBorder,1));
    LegendaryButton.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::LegendaryCardHover,7,ColdSteelUI::LegendaryText,1));
    LegendaryButton.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::LegendaryCardPressed,7,ColdSteelUI::LegendaryBorder,1));
    PrimaryButton=NormalButton;PrimaryButton.SetNormal(ColdSteelUI::RoundedBrush(Silver,7,Gray(245)));
    PrimaryButton.SetHovered(ColdSteelUI::RoundedBrush(Gray(244),7));PrimaryButton.SetPressed(ColdSteelUI::RoundedBrush(Gray(174),7));
    PrimaryButton.SetDisabled(ColdSteelUI::RoundedBrush(Gray(85),7));
    BackgroundTexture=LoadObject<UTexture2D>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_WorkshopBackground.T_WorkshopBackground"));
    BackgroundBrush.SetResourceObject(BackgroundTexture);BackgroundBrush.ImageSize=FVector2D(1672,941);BackgroundBrush.DrawAs=ESlateBrushDrawType::Image;
    LoadCategoryIcons();InitializePreview();
    if(IsStandaloneWorkbench())
        if(const auto* Item=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->FindItem(Model()->Instance()))
        {if(IsStaffWorkbench())SetStandaloneStaffItem(*Item);else if(IsBowWorkbench())SetStandaloneBowItem(*Item);else if(IsToolWorkbench())SetStandaloneToolItem(*Item);else SetStandaloneMeleeItem(*Item);}
    auto Button=[this](const FString& ButtonText,TFunction<void()> Fn,bool Primary=false)
    {
        return SNew(SButton).ButtonStyle(Primary?&PrimaryButton:&NormalButton).ContentPadding(FMargin(14,10))
            .IsEnabled_Lambda([this,Primary](){if(!Primary||!IsStandaloneWorkbench())return true;FString Reason;return Model()->CanApply(Reason);})
            .ToolTipText_Lambda([this,Primary](){return Primary?FText::FromString(Model()->ApplyFeedback()):FText::GetEmpty();})
            .OnClicked_Lambda([Fn](){Fn();return FReply::Handled();})
            [SNew(STextBlock).Text(FText::FromString(ButtonText)).Font(GunsmithUI::TextFont(14,true))
                .ColorAndOpacity(Primary?GunsmithUI::Gray(22):GunsmithUI::Text).MinDesiredWidth(84).Justification(ETextJustify::Center)];
    };
    const auto* W=Model()->ModifiableWeapon(Model()->Definition());
    const FString WeaponSubtitle=IsStaffWorkbench()?TEXT("   /   长杖 · 六槽改造"):IsBowWorkbench()?TEXT("   /   双手弓 · 五槽改造"):IsToolWorkbench()?TEXT("   /   采集工具"):IsMeleeWorkbench()?TEXT("   /   双手近战武器"):
        W&&W->Ammo==TEXT("ammo_357")?TEXT("   /   .357 Magnum"):W&&W->Ammo==TEXT("ammo_45acp")?TEXT("   /   .45 ACP"):
        W&&(W->Ammo==TEXT("ammo_9")||W->Ammo==TEXT("ammo_9mm"))?TEXT("   /   9 mm"):
        W&&W->Ammo==TEXT("ammo_58")?TEXT("   /   5.8 mm"):W&&W->Ammo==TEXT("ammo_762")?TEXT("   /   7.62 mm"):TEXT("   /   5.56 mm");
    auto Rail=SNew(SVerticalBox);
    Rail->AddSlot().AutoHeight().Padding(2,0,0,8)[Label(TEXT("可用部件"),12,Muted)];
    for(int32 I=0;I<Model()->Slots(Model()->Definition()).Num();++I)
    {
            const FString Key=Model()->Slots(Model()->Definition())[I],Name=Model()->CategoryLabel(Model()->Definition(),Key);
            if(!IsCategoryAvailable(Key))continue;
            TSharedRef<SWidget> IconContent=SNew(SImage).Image(CategoryBrushes.Contains(Key)?CategoryBrushes.FindChecked(Key).Get():FCoreStyle::Get().GetBrush("NoBrush"))
                .ColorAndOpacity(FLinearColor::White);
            if(IsStandaloneWorkbench()&&!CategoryBrushes.Contains(Key))
                IconContent=SNew(SMeleePartIcon).Part(Key).bTool(IsToolWorkbench()).Definition(Model()->Definition());
            if(!IsStandaloneWorkbench()||IsBowWorkbench()||IsStaffWorkbench())
                IconContent=SNew(SFramedAttachmentIcon).FramedImage(!IsStaffWorkbench()).Selected_Lambda([this,Key](){return SelectedCategory==Key;})
                    [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[IconContent]];
            auto Icon=SNew(SBox).WidthOverride(48).HeightOverride(48)
                [IconContent];
            auto Category=SNew(SButton).ButtonStyle(&NormalButton).ContentPadding(FMargin(8,7))
                .ToolTipText_Lambda([this,Name,Key](){return FText::FromString(Name+TEXT(" · ")+CategoryPartName(Key));})
                .OnClicked_Lambda([this,Key](){SelectCategory(Key);return FReply::Handled();})
                [SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Icon]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(8,0,0,0)
                    [SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight()[Label(Name,16,GunsmithUI::Text,true)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)
                        [SNew(STextBlock).Text_Lambda([this,Key](){return FText::FromString(CategoryPartName(Key));})
                            .Font(GunsmithUI::TextFont(12)).ColorAndOpacity(Secondary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]]];
            CategoryButtons.Add(Key,Category);
            Rail->AddSlot().AutoHeight().Padding(0,0,0,6)
                [SNew(SOverlay)+SOverlay::Slot()[Category]
                    +SOverlay::Slot().HAlign(HAlign_Left).Padding(0,12)
                    [SNew(SBox).WidthOverride(2)[SNew(SImage).Image(FCoreStyle::Get().GetBrush("WhiteBrush")).ColorAndOpacity(Silver)
                        .Visibility_Lambda([this,Key](){return SelectedCategory==Key?EVisibility::HitTestInvisible:EVisibility::Collapsed;})]]];
    }
    if(CategoryButtons.IsEmpty())Rail->AddSlot().AutoHeight()[Label(TEXT("当前武器暂无可用改造项目"),14,Secondary)];
    // 第五栏「强化」不是改造槽：不进 gunsmith_parts、不进 UGunsmithSystem::Slots()，因此不在上面的
    // Slots() 循环里；在循环之后单独追加一个同款式按钮，枪械与剑类的栏目来源不受影响。
    // 目录缺失（0 个等级）时整项隐藏，由详情区给「强化工具目录不可用」。
    if(IsToolWorkbench()&&!ColdSteelToolEnhance::Levels().IsEmpty())
    {
        const FString Enhance=TEXT("enhance");
        auto EnhanceCategory=SNew(SButton).ButtonStyle(&NormalButton).ContentPadding(FMargin(8,7))
            .ToolTipText(FText::FromString(TEXT("强化 · 金属材质档位")))
            .OnClicked_Lambda([this,Enhance](){SelectCategory(Enhance);return FReply::Handled();})
            [SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                [SNew(SBox).WidthOverride(48).HeightOverride(48)
                    [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
                        [SNew(SImage).Image(CategoryBrushes.Contains(Enhance)?CategoryBrushes.FindChecked(Enhance).Get():FCoreStyle::Get().GetBrush("NoBrush"))]]]
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(8,0,0,0)
                [SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight()[Label(TEXT("强化"),16,GunsmithUI::Text,true)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)
                    [SNew(STextBlock).Text_Lambda([this](){return FText::FromString(FString::Printf(TEXT("金属材质档位 · Lv.%d"),
                        Model()->CurrentEnhanceLevel()));})
                        .Font(GunsmithUI::TextFont(12)).ColorAndOpacity(Secondary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]]];
        CategoryButtons.Add(Enhance,EnhanceCategory);
        Rail->AddSlot().AutoHeight().Padding(0,0,0,6)
            [SNew(SOverlay)+SOverlay::Slot()[EnhanceCategory]
                +SOverlay::Slot().HAlign(HAlign_Left).Padding(0,12)
                [SNew(SBox).WidthOverride(2)[SNew(SImage).Image(FCoreStyle::Get().GetBrush("WhiteBrush")).ColorAndOpacity(Silver)
                    .Visibility_Lambda([this,Enhance](){return SelectedCategory==Enhance?EVisibility::HitTestInvisible:EVisibility::Collapsed;})]]];
    }
    RailContent=GlassPanel(SAssignNew(CategoryScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6)).AllowOverscroll(EAllowOverscroll::No)
        .ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)+SScrollBox::Slot()[Rail],FMargin(10));
    auto Header=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
        [SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight()[Label(TEXT("装备改造"),20,GunsmithUI::Text,true)]
            +SVerticalBox::Slot().AutoHeight().Padding(0,5,0,0)
            [Label((W?W->Name:TEXT("武器"))+WeaponSubtitle,12,Secondary)]]
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Button(TEXT("Esc  返回"),[this](){if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->CloseGunsmith();})];
    auto Stage=SNew(SOverlay)
        +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)[SNew(SImage).Image(&BackgroundBrush)]]
        +SOverlay::Slot().Padding(8,8,8,20)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
            [SNew(SImage).Image(&PreviewBrush).Visibility_Lambda([this](){return HasSelectedPreview()?EVisibility::HitTestInvisible:EVisibility::Collapsed;})]]
        +SOverlay::Slot().VAlign(VAlign_Top).HAlign(HAlign_Left).Padding(16)
        [SNew(STextBlock).Text(FText::FromString(TEXT("左键拖动旋转 · 滚轮缩放 · 双击复位"))).Font(GunsmithUI::TextFont(12)).ColorAndOpacity(Secondary)]
        +SOverlay::Slot().VAlign(VAlign_Bottom).HAlign(HAlign_Right).Padding(12)
        [SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth().Padding(0,0,8,0)[Button(TEXT("水平复位"),[this](){SetSidePreview(true);})]
            +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).Visibility(IsStandaloneWorkbench()?EVisibility::Collapsed:EVisibility::Visible)
                [Button(TEXT("瞄准预览"),[this](){SetAimPreview(true);})]]]
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
        [SNew(STextBlock).Text(FText::FromString(IsToolWorkbench()?TEXT("工具模型暂不可用"):IsMeleeWorkbench()?TEXT("武器模型暂不可用"):TEXT("该枪械尚未装备\n应用配置后装备查看")))
            .Font(GunsmithUI::TextFont(16)).ColorAndOpacity(GunsmithUI::Text).Justification(ETextJustify::Center)
            .Visibility_Lambda([this](){return HasSelectedPreview()?EVisibility::Collapsed:EVisibility::HitTestInvisible;})];
    auto Surface=SNew(SM4PreviewSurface).CanRotate_Lambda([this](){return HasSelectedPreview();})
        .OnOrbit_Lambda([this](FVector2D Delta){RotatePreview(Delta);}).OnZoom_Lambda([this](float Delta){ZoomPreview(Delta);}).OnReset_Lambda([this](){SetSidePreview(true);})[Stage];
    PreviewSurface=Surface;
    auto OptionsHeader=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text_Lambda([this](){return FText::FromString(OptionsTitle());}).Font(GunsmithUI::TextFont(16,true)).ColorAndOpacity(GunsmithUI::Text)]
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
        [SNew(STextBlock).Text_Lambda([this](){return FText::FromString(FString::Printf(TEXT("%d 项 · 滚轮浏览"),OptionsCount()));}).Font(GunsmithUI::TextFont(12)).ColorAndOpacity(Muted)];
    auto Options=SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight().Padding(0,0,0,10)[OptionsHeader]
        +SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride(158)
            [SAssignNew(OptionScroll,SScrollBox).Orientation(Orient_Horizontal).ScrollBarThickness(FVector2D(6,6)).ScrollBarAlwaysVisible(true)
                .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::Always).WheelScrollMultiplier(2.f).AnimateWheelScrolling(false)]];
    CenterContent=SNew(SVerticalBox)
        +SVerticalBox::Slot().FillHeight(1)[SNew(SBorder).BorderImage(&PanelBrush).Padding(1).Clipping(EWidgetClipping::ClipToBounds)[Surface]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,12,0,0)[GlassPanel(Options)];
    auto CompareButton=[this](bool Factory)
    {
        return SNew(SBorder).Padding(1).BorderImage_Lambda([this,Factory]()->const FSlateBrush*{return bCompareFactory==Factory?&SelectedButton.Normal:FCoreStyle::Get().GetBrush("NoBrush");})
            [SNew(SButton).ButtonStyle(&NormalButton).ContentPadding(FMargin(10,8)).OnClicked_Lambda([this,Factory](){SetCompareFactory(Factory);return FReply::Handled();})
                [Label(Factory?TEXT("对比原厂"):TEXT("对比当前"),14)]];
    };
    auto TableHeader=SNew(SHorizontalBox);
    const float Columns[]={1.55f,.94f,.94f,.83f};
    for(int32 Column=0;Column<4;++Column)
        TableHeader->AddSlot().FillWidth(Columns[Column]).Padding(4,4)
        [SNew(STextBlock).Text_Lambda([this,Column](){return FText::FromString(Column==0?TEXT("项目"):Column==1?(bCompareFactory?TEXT("原厂"):TEXT("当前")):Column==2?TEXT("改造后"):TEXT("变化"));})
            .Font(GunsmithUI::TextFont(12,true)).ColorAndOpacity(Secondary).Justification(Column?ETextJustify::Right:ETextJustify::Left)];
    auto OverviewPanel=SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[Label(IsStaffWorkbench()?TEXT("长杖数值总览"):IsToolWorkbench()?TEXT("采集数值总览"):IsMeleeWorkbench()?TEXT("近战数值总览"):TEXT("整枪数值总览"),20,GunsmithUI::Text,true)]
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,4,0)[CompareButton(false)]
            +SHorizontalBox::Slot().FillWidth(1).Padding(4,0,0,0)[CompareButton(true)]]
        +SVerticalBox::Slot().AutoHeight()[TableHeader]
        +SVerticalBox::Slot().FillHeight(1)[SAssignNew(OverviewScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6)).AllowOverscroll(EAllowOverscroll::No)
            .ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)+SScrollBox::Slot()[SAssignNew(OverviewList,SVerticalBox)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[Label(TEXT("绿色 增强  /  红色 削弱  /  灰色 不变"),12,Muted)];
    InspectorContent=GlassPanel(SAssignNew(InspectorScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6))
        .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
        +SScrollBox::Slot()[SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[Label(TEXT("当前配件详情"),16,GunsmithUI::Text,true)]
            +SVerticalBox::Slot().AutoHeight()[SNew(SBox).MinDesiredHeight(280).VAlign(VAlign_Top)[SAssignNew(ModificationList,SVerticalBox)]]
            +SVerticalBox::Slot().AutoHeight().Padding(0,16,0,0)
            [SNew(SBox).HeightOverride_Lambda([this](){return OverviewSectionHeight();})[OverviewPanel]]]);
    FooterContent=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,12,0)
        [SNew(STextBlock).Text_Lambda([this](){return FText::FromString(StatusText);}).Font(GunsmithUI::TextFont(14)).ColorAndOpacity(Secondary).AutoWrapText(true)]
        +SHorizontalBox::Slot().AutoWidth().Padding(0,0,10,0)[Button(TEXT("撤销更改"),[this](){UndoDraft();})]
        +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("应用并保存"),[this](){ApplyDraft();},true)];
    auto Content=SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight().Padding(22,18,22,16)[Header]
        +SVerticalBox::Slot().FillHeight(1).Padding(18,0)[SAssignNew(BodyHost,SBox)]
        +SVerticalBox::Slot().AutoHeight().Padding(22,14,22,18)[FooterContent.ToSharedRef()];
    UpdateResponsiveLayout();
    // Cancel UE's resolution curve; reflow the real space instead of shrinking a fixed canvas.
    return SNew(SDPIScaler).DPIScale_Lambda([this](){return 1.f/ColdSteelUI::PixelScale(this);})
        [SNew(SOverlay)
            +SOverlay::Slot()[SNew(SSimpleGradient).StartColor(FLinearColor(.075f,.075f,.075f)).EndColor(FLinearColor(.24f,.24f,.24f)).Orientation(Orient_Vertical)]
            +SOverlay::Slot()[SNew(SSimpleGradient).StartColor(FLinearColor(1,1,1,.025f)).EndColor(FLinearColor(0,0,0,.25f)).Orientation(Orient_Horizontal)]
            +SOverlay::Slot()[Content]];
}

void UM4GunsmithWidget::UpdateResponsiveLayout()
{
    if(!BodyHost||!RailContent||!CenterContent||!InspectorContent)return;
    FVector2D Size=BodyHost->GetCachedGeometry().GetLocalSize();if(Size.X<100)Size=FVector2D(1500,740);
    const int32 Mode=Size.X<740?3:(Size.X<1240||Size.Y<520)?2:Size.X<1450?1:0;
    if(LayoutMode==Mode)return;
    LayoutMode=Mode;RailWidth=Mode==0?208.f:184.f;InspectorWidth=Mode==0?560.f:500.f;
    BodyHost->SetContent(SNullWidget::NullWidget);BodyScroll.Reset();
    if(Mode<2)
        BodyHost->SetContent(SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().Padding(0,0,12,0)[SNew(SBox).WidthOverride(RailWidth)[RailContent.ToSharedRef()]]
            +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,12,0)[CenterContent.ToSharedRef()]
            +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(InspectorWidth)[InspectorContent.ToSharedRef()]]);
    else
    {
        auto Flow=SNew(SVerticalBox);
        if(Mode==2)
            Flow->AddSlot().AutoHeight()[SNew(SBox).HeightOverride(610)
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().Padding(0,0,12,0)[SNew(SBox).WidthOverride(RailWidth)[RailContent.ToSharedRef()]]
                    +SHorizontalBox::Slot().FillWidth(1)[CenterContent.ToSharedRef()]]];
        else
        {
            Flow->AddSlot().AutoHeight()[SNew(SBox).HeightOverride(240)[RailContent.ToSharedRef()]];
            Flow->AddSlot().AutoHeight().Padding(0,12,0,0)[SNew(SBox).HeightOverride(530)[CenterContent.ToSharedRef()]];
        }
        Flow->AddSlot().AutoHeight().Padding(0,12,0,0)
            [SNew(SBox).HeightOverride_Lambda([this](){return FMath::Max(820.f,float(BodyHost->GetCachedGeometry().GetLocalSize().Y));})[InspectorContent.ToSharedRef()]];
        BodyHost->SetContent(SAssignNew(BodyScroll,SScrollBox).ScrollBarThickness(FVector2D(8,8)).AllowOverscroll(EAllowOverscroll::No)
            .ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)+SScrollBox::Slot()[Flow]);
    }
    PreviewMotion=1.f;
    UE_LOG(LogTemp,Display,TEXT("COLD_GLASS_LAYOUT mode=%d body=%.0fx%.0f rail=%.0f inspector=%.0f icons=%d"),Mode,Size.X,Size.Y,RailWidth,InspectorWidth,CategoryBrushes.Num());
}

TSharedRef<SWidget> UM4GunsmithWidget::BuildOption(const FString& SlotKey,const FString& Id)
{
    const auto* O=Model()->Option(Model()->Definition(),SlotKey,Id);if(!O)return SNew(SBox);
    const FString Weapon=Model()->Definition();
    const auto Tier=ColdSteelModification::Tier(Weapon,SlotKey,Id);
    const bool Exclusive=Tier==EGunsmithModificationTier::Special;
    const bool Legendary=Tier==EGunsmithModificationTier::Legendary;
    const FLinearColor TierColor=Legendary?ColdSteelUI::LegendaryText:Exclusive?ColdSteelUI::ExclusiveText:GunsmithUI::Text;
    FString Summary=O->Description.Replace(TEXT("\r"),TEXT(" ")).Replace(TEXT("\n"),TEXT(" "));
    if(Summary.Len()>46)Summary=Summary.Left(46)+TEXT("…");
    auto Selected=[this,SlotKey,Id](){return Model()->Draft().FindRef(SlotKey)==Id||(Id==TEXT("false")&&!Model()->Draft().Contains(SlotKey));};
    auto Installed=[this,SlotKey,Id](){
        const auto* Item=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->FindItem(Model()->Instance());
        if(!Item)return false;
        const FString Active=Model()->Installed(*Item).FindRef(SlotKey);
        return Active==Id||(Id==TEXT("false")&&Active.IsEmpty());
    };
    // Follow the current draft selection, including an accessory awaiting Apply.
    auto Neon=[Selected,Id](){return Id!=TEXT("false")&&Selected();};
    auto Frame=[Neon,Selected,Exclusive,Legendary](){auto C=ColdSteelUI::Success;C.A=.32f;return Neon()?C:Selected()?GunsmithUI::Silver:Legendary?ColdSteelUI::LegendaryBorder:Exclusive?ColdSteelUI::ExclusiveBorder:FLinearColor::Transparent;};
    FString IconDirectory=FPaths::ProjectContentDir()/TEXT("ColdSteelData/AttachmentIcons20260913");
    // Retained RSH models keep their existing pictograms; only catalog identity changes.
    const FString IconId=Weapon==TEXT("ue_rsh12")&&SlotKey==TEXT("optic")?RSH12OpticAssets::SourceVariant(Id):Id;
    const FString WeaponIconKey=Model()->Definition()+TEXT("_")+SlotKey+TEXT("_")+IconId;
    // The shared fast-trigger pictogram also represents Pit Viper's numeric option.
    const FString CommonIconKey=SlotKey==TEXT("trigger")&&Id==TEXT("pit_viper_lightweight_fast")
        ?TEXT("trigger_m1911_lightweight_fast"):SlotKey+TEXT("_")+IconId;
    const FString FramedDirectory=IconDirectory/(IsBowWorkbench()?TEXT("FramedBows"):TEXT("FramedFirearms"));
    const bool SharedFirearmOption=!IsStandaloneWorkbench()&&Id!=TEXT("false")
        &&FPaths::FileExists(FramedDirectory/(CommonIconKey+TEXT(".png")));
    const bool Framed=SharedFirearmOption||((!IsStandaloneWorkbench()||IsBowWorkbench())&&(FPaths::FileExists(FramedDirectory/(WeaponIconKey+TEXT(".png")))
        ||(!FPaths::FileExists(IconDirectory/(WeaponIconKey+TEXT(".png")))
            &&FPaths::FileExists(FramedDirectory/(CommonIconKey+TEXT(".png"))))));
    if(Framed)IconDirectory=FramedDirectory;
    // Common modifications share one brush; factory parts retain their weapon key.
    // A common melee option has one icon across every compatible weapon.
    // Keep exclusive modifications and factory parts on their own authored keys.
    const bool SharedMeleeOption=IsMeleeWorkbench()&&!Legendary&&Id!=TEXT("false")
        &&FPaths::FileExists(IconDirectory/(CommonIconKey+TEXT(".png")));
    const bool UseWeaponIcon=!SharedFirearmOption&&!SharedMeleeOption
        &&FPaths::FileExists(IconDirectory/(WeaponIconKey+TEXT(".png")));
    const FString IconKey=UseWeaponIcon?WeaponIconKey:CommonIconKey;
    if(!AttachmentBrushes.Contains(IconKey)&&FPaths::FileExists(IconDirectory/(IconKey+TEXT(".png"))))
    {
        const FString IconPath=IconDirectory/(IconKey+TEXT(".png"));
        if(auto* Texture=FImageUtils::ImportFileAsTexture2D(IconPath))
        {
            AttachmentTextures.Add(Texture);
            auto Brush=MakeShared<FSlateBrush>();Brush->ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());
            Brush->DrawAs=ESlateBrushDrawType::Image;Brush->SetResourceObject(Texture);
            AttachmentBrushes.Add(IconKey,Brush);
        }
    }
    const FSlateBrush* Icon=AttachmentBrushes.Contains(IconKey)?AttachmentBrushes.FindChecked(IconKey).Get():
        (CategoryBrushes.Contains(SlotKey)?CategoryBrushes.FindChecked(SlotKey).Get():FCoreStyle::Get().GetBrush("NoBrush"));
    TSharedRef<SWidget> OptionIcon=SNew(SImage).Image(Icon).ToolTipText(FText::FromString(O->Name));
    if(IsStandaloneWorkbench()&&!IsBowWorkbench()&&AttachmentBrushes.Contains(IconKey))OptionIcon=SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[OptionIcon];
    if(IsStandaloneWorkbench()&&!AttachmentBrushes.Contains(IconKey))
        OptionIcon=SNew(SMeleePartIcon).Part(SlotKey).bTool(IsToolWorkbench()).Definition(Model()->Definition());
    if(!IsStandaloneWorkbench()||IsBowWorkbench()||IsStaffWorkbench())
        OptionIcon=SNew(SFramedAttachmentIcon).FramedImage(!IsStaffWorkbench()).Selected_Lambda(Selected).Installed_Lambda(Installed)
            [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[OptionIcon]];
    FString Appearance;
    // 工具四栏当前是数值改造：外观说明直接取目录的 appearance 字段，不查剑类模块 JSON。
    if(IsToolWorkbench()||IsBowWorkbench()||IsStaffWorkbench())Appearance=O->Appearance;
    else if(IsMeleeWorkbench())if(const auto* Item=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->FindItem(Model()->Instance()))
        Appearance=ColdSteelModularSword::Appearance(*Item,SlotKey,Id);
    return SNew(SBox).WidthOverride(IsStandaloneWorkbench()?288:264).HeightOverride(142)
        [SNew(SOverlay)+SOverlay::Slot()
        [SNew(SBorder).Padding(2).BorderImage(&OptionFrameBrush).BorderBackgroundColor_Lambda(Frame)
        [SNew(SButton).ButtonStyle(Legendary?&LegendaryButton:Exclusive?&ExclusiveButton:&NormalButton).ContentPadding(FMargin(10,8)).ToolTipText(FText::FromString(O->Name+TEXT("\n")+O->Description))
            .OnClicked_Lambda([this,SlotKey,Id](){ChooseOption(SlotKey,Id);return FReply::Handled();})
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[Label(O->Name,16,TierColor,true)]
                +SVerticalBox::Slot().FillHeight(1).Padding(0,5,0,5)
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,10,0)
                    [SNew(SBox).WidthOverride(64).HeightOverride(64)
                        [OptionIcon]]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                    [SNew(SBox).Clipping(EWidgetClipping::ClipToBounds)
                        [SNew(SVerticalBox)
                            +SVerticalBox::Slot().AutoHeight()[Label(Summary,12,GunsmithUI::Secondary)]
                            +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)
                            [SNew(STextBlock).Text(FText::FromString(Appearance)).Font(GunsmithUI::TextFont(11)).ColorAndOpacity(GunsmithUI::Muted)
                                .Visibility(Appearance.IsEmpty()?EVisibility::Collapsed:EVisibility::HitTestInvisible).AutoWrapText(true)]]]]
                +SVerticalBox::Slot().AutoHeight()
                [SNew(SOverlay)
                    +SOverlay::Slot()[SNew(SImage).Image(FCoreStyle::Get().GetBrush("WhiteBrush"))
                        .ColorAndOpacity_Lambda([Neon](){auto C=ColdSteelUI::Success;C.A=Neon()?.08f:0.f;return C;}).Visibility(EVisibility::HitTestInvisible)]
                    +SOverlay::Slot().Padding(6,2)
                    [SNew(STextBlock).Text_Lambda([Selected,Installed,Id,Tier](){
                        const FString Status=Installed()?(Id==TEXT("false")?TEXT("当前原厂配置"):TEXT("已安装")):(Selected()?TEXT("已选 · 待应用"):TEXT("选择配件"));
                        return FText::FromString(FString(Id==TEXT("false")?TEXT(""):ColdSteelModification::Label(Tier))+(Id==TEXT("false")?TEXT(""):TEXT(" · "))+Status);})
                        .Font(GunsmithUI::TextFont(12,true))
                        .ColorAndOpacity_Lambda([Neon,Selected,TierColor](){return Neon()?ColdSteelUI::Success:Selected()?GunsmithUI::Silver:TierColor;})
                        .ShadowOffset(FVector2D(0,1)).ShadowColorAndOpacity(FLinearColor(0,0,0,.4f))]]]]]
            +SOverlay::Slot()[SNew(SAttachmentSelectionPulse).Active_Lambda(Neon)]];
}
