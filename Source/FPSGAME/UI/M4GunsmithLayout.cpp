#include "M4GunsmithWidget.h"
#include "SM4PreviewSurface.h"
#include "SAttachmentSelectionPulse.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
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
    for(const auto& Key:Model()->Slots())
    {
        if(!IsCategoryAvailable(Key))continue;
        const FString IconDirectory=FPaths::ProjectContentDir()/TEXT("ColdSteelData/AttachmentIcons20260913");
        const FString WeaponIconPath=IconDirectory/(Model()->Definition()+TEXT("_category_")+Key+TEXT(".png"));
        const FString IconPath=FPaths::FileExists(WeaponIconPath)?WeaponIconPath:IconDirectory/(TEXT("category_")+Key+TEXT(".png"));
        if(auto* Texture=FImageUtils::ImportFileAsTexture2D(IconPath))
        {
            CategoryTextures.Add(Texture);
            auto Brush=MakeShared<FSlateBrush>();Brush->ImageSize=FVector2D(48,48);
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
    const auto* W=Model()->Weapon(Model()->Definition());
    if(!W||!W->Allowed.Contains(Key))return TEXT("待扩展");
    const FString Id=Model()->Draft().FindRef(Key);
    if(const auto* O=Model()->Option(Model()->Definition(),Key,Id.IsEmpty()?TEXT("false"):Id))return O->Name;
    return TEXT("原厂配置");
}

TSharedRef<SWidget> UM4GunsmithWidget::BuildWorkbench()
{
    using namespace GunsmithUI;
    OptionsSignature.Reset();OptionsCategory.Reset();InspectedOptionKey.Reset();OptionCards.Reset();CategoryButtons.Reset();GlassLayers.Reset();LayoutMode=-1;
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
    PrimaryButton=NormalButton;PrimaryButton.SetNormal(ColdSteelUI::RoundedBrush(Silver,7,Gray(245)));
    PrimaryButton.SetHovered(ColdSteelUI::RoundedBrush(Gray(244),7));PrimaryButton.SetPressed(ColdSteelUI::RoundedBrush(Gray(174),7));
    PrimaryButton.SetDisabled(ColdSteelUI::RoundedBrush(Gray(85),7));
    BackgroundTexture=LoadObject<UTexture2D>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_WorkshopBackground.T_WorkshopBackground"));
    BackgroundBrush.SetResourceObject(BackgroundTexture);BackgroundBrush.ImageSize=FVector2D(1672,941);BackgroundBrush.DrawAs=ESlateBrushDrawType::Image;
    LoadCategoryIcons();InitializePreview();
    auto Button=[this](const FString& ButtonText,TFunction<void()> Fn,bool Primary=false)
    {
        return SNew(SButton).ButtonStyle(Primary?&PrimaryButton:&NormalButton).ContentPadding(FMargin(14,10))
            .OnClicked_Lambda([Fn](){Fn();return FReply::Handled();})
            [SNew(STextBlock).Text(FText::FromString(ButtonText)).Font(GunsmithUI::TextFont(14,true))
                .ColorAndOpacity(Primary?GunsmithUI::Gray(22):GunsmithUI::Text).MinDesiredWidth(84).Justification(ETextJustify::Center)];
    };
    const auto* W=Model()->Weapon(Model()->Definition());
    auto Rail=SNew(SVerticalBox);
    Rail->AddSlot().AutoHeight().Padding(2,0,0,8)[Label(TEXT("可用部件"),12,Muted)];
    for(int32 I=0;I<Model()->Slots().Num();++I)
    {
            const FString Key=Model()->Slots()[I],Name=Model()->Categories()[I];
            if(!IsCategoryAvailable(Key))continue;
            auto Icon=SNew(SBox).WidthOverride(48).HeightOverride(48)
                [SNew(SImage).Image(CategoryBrushes.Contains(Key)?CategoryBrushes.FindChecked(Key).Get():FCoreStyle::Get().GetBrush("NoBrush"))
                    .ColorAndOpacity(FLinearColor::White)];
            auto Category=SNew(SButton).ButtonStyle(&NormalButton).ContentPadding(FMargin(8,7))
                .ToolTipText_Lambda([this,Name,Key](){return FText::FromString(Name+TEXT(" · ")+CategoryPartName(Key));})
                .OnClicked_Lambda([this,Key](){SelectCategory(Key);return FReply::Handled();})
                [SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Icon]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(8,0,0,0)
                    [SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight()[Label(Name,16,Text,true)]
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
    RailContent=GlassPanel(SAssignNew(CategoryScroll,SScrollBox).ScrollBarThickness(FVector2D(6,6)).AllowOverscroll(EAllowOverscroll::No)
        .ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)+SScrollBox::Slot()[Rail],FMargin(10));
    auto Header=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
        [SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight()[Label(TEXT("装备改造"),20,Text,true)]
            +SVerticalBox::Slot().AutoHeight().Padding(0,5,0,0)
            [Label((W?W->Name:TEXT("武器"))+(W&&W->Ammo==TEXT("ammo_357")?TEXT("   /   .357 Magnum"):W&&W->Ammo==TEXT("ammo_45acp")?TEXT("   /   .45 ACP"):W&&W->Ammo==TEXT("ammo_58")?TEXT("   /   5.8 mm"):W&&W->Ammo==TEXT("ammo_762")?TEXT("   /   7.62 mm"):TEXT("   /   5.56 mm")),12,Secondary)]]
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Button(TEXT("Esc  返回"),[this](){if(auto* PC=Cast<AFPSGAMEPlayerController>(GetOwningPlayer()))PC->CloseGunsmith();})];
    auto Stage=SNew(SOverlay)
        +SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFill)[SNew(SImage).Image(&BackgroundBrush)]]
        +SOverlay::Slot().Padding(8,8,8,20)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
            [SNew(SImage).Image(&PreviewBrush).Visibility_Lambda([this](){auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();return P->Equipped()&&P->Equipped()->InstanceId==Model()->Instance()?EVisibility::HitTestInvisible:EVisibility::Collapsed;})]]
        +SOverlay::Slot().VAlign(VAlign_Top).HAlign(HAlign_Left).Padding(16)
        [SNew(STextBlock).Text(FText::FromString(TEXT("左键拖动旋转 · 滚轮缩放 · 双击复位"))).Font(GunsmithUI::TextFont(12)).ColorAndOpacity(Secondary)]
        +SOverlay::Slot().VAlign(VAlign_Bottom).HAlign(HAlign_Right).Padding(12)
        [SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth().Padding(0,0,8,0)[Button(TEXT("水平复位"),[this](){SetSidePreview(true);})]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("瞄准预览"),[this](){SetAimPreview(true);})]]
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
        [SNew(STextBlock).Text(FText::FromString(TEXT("该枪械尚未装备\n应用配置后装备查看")))
            .Font(GunsmithUI::TextFont(16)).ColorAndOpacity(Text).Justification(ETextJustify::Center)
            .Visibility_Lambda([this](){auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();return P->Equipped()&&P->Equipped()->InstanceId==Model()->Instance()?EVisibility::Collapsed:EVisibility::HitTestInvisible;})];
    auto Surface=SNew(SM4PreviewSurface).CanRotate_Lambda([this](){auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();return P->Equipped()&&P->Equipped()->InstanceId==Model()->Instance();})
        .OnOrbit_Lambda([this](FVector2D Delta){RotatePreview(Delta);}).OnZoom_Lambda([this](float Delta){ZoomPreview(Delta);}).OnReset_Lambda([this](){SetSidePreview(true);})[Stage];
    PreviewSurface=Surface;
    auto OptionsHeader=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text_Lambda([this](){const int32 Index=Model()->Slots().IndexOfByKey(SelectedCategory);return FText::FromString((Model()->Categories().IsValidIndex(Index)?Model()->Categories()[Index]:TEXT("配件"))+TEXT(" / 可选配件"));}).Font(GunsmithUI::TextFont(16,true)).ColorAndOpacity(Text)]
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
        [SNew(STextBlock).Text_Lambda([this](){return FText::FromString(FString::Printf(TEXT("%d 项 · 滚轮浏览"),OptionCards.Num()));}).Font(GunsmithUI::TextFont(12)).ColorAndOpacity(Muted)];
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
        +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[Label(TEXT("整枪数值总览"),20,Text,true)]
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
            +SVerticalBox::Slot().AutoHeight().Padding(0,0,0,8)[Label(TEXT("当前配件详情"),16,Text,true)]
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
    auto Frame=[Neon,Selected](){auto C=ColdSteelUI::Success;C.A=.32f;return Neon()?C:Selected()?GunsmithUI::Silver:FLinearColor::Transparent;};
    const FString IconDirectory=FPaths::ProjectContentDir()/TEXT("ColdSteelData/AttachmentIcons20260913");
    const FString CommonIconKey=SlotKey+TEXT("_")+Id;
    const FString WeaponIconKey=Model()->Definition()+TEXT("_")+CommonIconKey;
    // Cache the resolved weapon-specific image so switching guns keeps each factory part distinct.
    const FString IconKey=FPaths::FileExists(IconDirectory/(WeaponIconKey+TEXT(".png")))?WeaponIconKey:CommonIconKey;
    if(!AttachmentBrushes.Contains(IconKey))
    {
        const FString IconPath=IconDirectory/(IconKey+TEXT(".png"));
        if(auto* Texture=FImageUtils::ImportFileAsTexture2D(IconPath))
        {
            AttachmentTextures.Add(Texture);
            auto Brush=MakeShared<FSlateBrush>();Brush->ImageSize=FVector2D(64,64);
            Brush->DrawAs=ESlateBrushDrawType::Image;Brush->SetResourceObject(Texture);
            AttachmentBrushes.Add(IconKey,Brush);
        }
    }
    const FSlateBrush* Icon=AttachmentBrushes.Contains(IconKey)?AttachmentBrushes.FindChecked(IconKey).Get():
        (CategoryBrushes.Contains(SlotKey)?CategoryBrushes.FindChecked(SlotKey).Get():FCoreStyle::Get().GetBrush("NoBrush"));
    return SNew(SBox).WidthOverride(264).HeightOverride(142)
        [SNew(SOverlay)+SOverlay::Slot()
        [SNew(SBorder).Padding(2).BorderImage(&OptionFrameBrush).BorderBackgroundColor_Lambda(Frame)
        [SNew(SButton).ButtonStyle(&NormalButton).ContentPadding(FMargin(10,8)).ToolTipText(FText::FromString(O->Name+TEXT("\n")+O->Description))
            .OnClicked_Lambda([this,SlotKey,Id](){ChooseOption(SlotKey,Id);return FReply::Handled();})
            [SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()[Label(O->Name,16,GunsmithUI::Text,true)]
                +SVerticalBox::Slot().FillHeight(1).Padding(0,5,0,5)
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,10,0)
                    [SNew(SBox).WidthOverride(64).HeightOverride(64)
                        [SNew(SImage).Image(Icon).ToolTipText(FText::FromString(O->Name))]]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                    [SNew(SBox).Clipping(EWidgetClipping::ClipToBounds)[Label(Summary,12,GunsmithUI::Secondary)]]]
                +SVerticalBox::Slot().AutoHeight()
                [SNew(SOverlay)
                    +SOverlay::Slot()[SNew(SImage).Image(FCoreStyle::Get().GetBrush("WhiteBrush"))
                        .ColorAndOpacity_Lambda([Neon](){auto C=ColdSteelUI::Success;C.A=Neon()?.08f:0.f;return C;}).Visibility(EVisibility::HitTestInvisible)]
                    +SOverlay::Slot().Padding(6,2)
                    [SNew(STextBlock).Text_Lambda([Selected,Installed,Id](){
                        return FText::FromString(Installed()?(Id==TEXT("false")?TEXT("当前原厂配置"):TEXT("已安装")):(Selected()?TEXT("已选 · 待应用"):TEXT("选择配件")));})
                        .Font(GunsmithUI::TextFont(12,true))
                        .ColorAndOpacity_Lambda([Neon,Selected](){return Neon()?ColdSteelUI::Success:Selected()?GunsmithUI::Silver:GunsmithUI::Muted;})
                        .ShadowOffset(FVector2D(0,1)).ShadowColorAndOpacity(FLinearColor(0,0,0,.4f))]]]]]
            +SOverlay::Slot()[SNew(SAttachmentSelectionPulse).Active_Lambda(Neon)]];
}
