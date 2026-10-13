// Woodworking layout only. Included after the shared input canvas in the widget translation unit.
class SWoodworkingPanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SWoodworkingPanel){} SLATE_ARGUMENT(UColdSteelWoodworkingWidget*,Owner) SLATE_END_ARGS()
    void Construct(const FArguments& Args)
    {
        Owner=Args._Owner;SetClipping(EWidgetClipping::ClipToBounds);SetVisibility(EVisibility::SelfHitTestInvisible);Canvas=SNew(SWoodworkingCanvas).Owner(Owner.Get());
        if(auto* M=Owner->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        {Model=M;InventoryHandle=M->OnChanged.AddLambda([this](){bQuoteDirty=true;});}
        Build();
    }
    virtual ~SWoodworkingPanel() override {if(Model.IsValid())Model->OnChanged.Remove(InventoryHandle);}
    void CancelInput(){Canvas->Cancel();}
    bool Confirming() const {return bConfirmClose;}
    void AskClose(bool Return=false){CancelInput();bConfirmClose=true;bReturnToSelection=Return;Build();}
    void ResetConfirm(){bConfirmClose=bReturnToSelection=false;Canvas->ClearFeedback();Canvas->SetBlocked(false);bQuoteDirty=true;}
    void Undo(){CancelInput();if(Owner->PresentationReady()&&Owner->System()->Undo()){Canvas->ClearFeedback();Owner->BoardChanged();}Refresh();}
    void Rotate(int32 Direction,bool Fine=false){if(!bConfirmClose&&Owner->PresentationReady())Canvas->Rotate(Direction,Fine);Refresh();}
    void ToggleCutting()
    {
        if(bConfirmClose||!Owner->PresentationReady()||!Owner->EnsureStation())return;
        if(Owner->System()->State()==EWoodworkingPhase::Preview){Primary();return;}
        CancelInput();const uint64 Before=Owner->System()->Mask().CutSerial();
        Owner->System()->ToggleMotor();Canvas->Contact(Before);Refresh();
    }
    virtual void Tick(const FGeometry& Geometry,double,float) override
    {
        if(!Owner.IsValid()||!Owner->System())return;
        const float CurrentScale=FMath::Max(.1f,ColdSteelUI::PixelScale(Owner.Get()));
        const FVector2D CurrentSize=Geometry.GetLocalSize()*CurrentScale;
        if(CurrentSize.X>100&&CurrentSize.Y>100&&(!CurrentSize.Equals(AvailablePixels,1)||!FMath::IsNearlyEqual(CurrentScale,Scale)))
        {AvailablePixels=CurrentSize;Build();return;}
        const bool Result=IsResult();
        if(Owner->IsProjectMenu()&&(BuiltJobId!=Owner->System()->Job().Id||bBuiltFinished!=Owner->System()->Job().bFinished)){Build();return;}
        if(Result!=bBuiltResult&&!Owner->IsProjectMenu()){Build();return;}
        const double Now=FPlatformTime::Seconds();
        if(Now>=NextRefresh){Refresh();NextRefresh=Now+.1;}
    }
    void Build()
    {
        CancelInput();ChildSlot.HAlign(HAlign_Fill).VAlign(VAlign_Fill).Padding(0)[SNullWidget::NullWidget];
        Scale=FMath::Max(.1f,ColdSteelUI::PixelScale(Owner.Get()));Buttons=ColdSteelUI::ButtonStyle(Scale);
        Frame=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale);
        Fallback=ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,ColdSteelUI::PanelRadius/Scale);
        Title.Reset();Mode.Reset();Time.Reset();Clearance.Reset();Integrity.Reset();Message.Reset();PrimaryText.Reset();Motor.Reset();
        bBuiltResult=IsResult();bQuoteDirty=true;BuiltJobId=Owner->System()->Job().Id;bBuiltFinished=Owner->System()->Job().bFinished;
        if(Owner->IsProjectMenu())BuildSelection();else BuildWorkshop();
        Canvas->SetBlocked(Owner->IsProjectMenu()||bConfirmClose||bBuiltResult);
        Owner->SetReviewOverlay(bBuiltResult);Refresh();
    }
    void Refresh()
    {
        if(!Owner.IsValid()||!Owner->System())return;auto* S=Owner->System();
        if(bQuoteDirty)
        {
            bQuoteDirty=false;QuoteReason.Reset();bCanStart=S->CanStartMode(EWoodworkingMode::Craft,QuoteReason);
        }
        const auto* P=S->Pattern();const auto Phase=S->State();
        if(Owner->IsProjectMenu())return;
        const bool Preview=Phase==EWoodworkingPhase::Preview,Running=Phase==EWoodworkingPhase::Running;
        Set(Title,(bBuiltResult?(Phase==EWoodworkingPhase::Failed?FString(TEXT("加工未达标")):FString(TEXT("加工完成"))):S->IsAdjusting()?FString(TEXT("调整木板")):FString(TEXT("正在切割")))+TEXT(" · ")+(P?P->Name:FString()));
        Set(Mode,FString::Printf(TEXT("材料已投入 · 角度 %.2f°"),FMath::RadiansToDegrees(S->Pose().Angle)));
        const FString Clock=FString::Printf(TEXT("剩余 %.1f 秒"),S->Remaining());
        Set(Time,Clock+(Preview?TEXT(" · 未计时"):S->IsAdjusting()?TEXT(" · 暂停"):TEXT("")));
        const auto Metrics=S->Mask().Metrics();
        Set(Clearance,FString::Printf(TEXT("清除 %.1f%% / %.1f%%"),Metrics.Clearance*100,S->Settings().RequiredClearance*100));
        Set(Integrity,FString::Printf(TEXT("损伤 %.1f%% / ≤%.1f%%"),(1-Metrics.Integrity)*100,S->Settings().MaximumDamage*100));
        if(Integrity)Integrity->SetColorAndOpacity(Metrics.Integrity<1-S->Settings().MaximumDamage*.75?ColdSteelUI::Danger:ColdSteelUI::TextPrimary);
        if(Time)Time->SetColorAndOpacity(S->MotorRunning()&&S->IsTimed()&&S->Remaining()<15?ColdSteelUI::Danger:ColdSteelUI::TextPrimary);
        Set(Motor,S->MotorRunning()?TEXT("调整方向 · 空格"):TEXT("进入切割 · 空格"));
        Set(PrimaryText,Preview?TEXT("进入切割 · 空格"):Running?TEXT("完成加工"):
            Phase==EWoodworkingPhase::Complete&&!S->IsPractice()?TEXT("领取成品"):TEXT("再做一次"));
        FString Notice=Owner->PresentationStatus();if(Notice.IsEmpty())Notice=S->Message();
        if(S->IsAdjusting())Notice+=TEXT(" 虚线预览落刀位置，进入切割会切除锯口覆盖的木料。");
        if(Preview&&!bCanStart)Notice=QuoteReason;
        if(bConfirmClose)Notice=TEXT("结束加工并返回工作面板处理工件。");
        Set(Message,Notice);
    }
private:
    static void Set(const TSharedPtr<STextBlock>& T,const FString& Text){if(T&&T->GetText().ToString()!=Text)T->SetText(FText::FromString(Text));}
    bool IsResult() const {const auto P=Owner->System()->State();return P==EWoodworkingPhase::Complete||P==EWoodworkingPhase::Failed||P==EWoodworkingPhase::Delivered;}
    FVector2D ScreenSize() const {return AvailablePixels.X>100?AvailablePixels:UWidgetLayoutLibrary::GetViewportSize(Owner.Get());}
    TSharedRef<STextBlock> Label(const FString& Text,float Size=14,bool Numeric=false,bool Wrap=false)
    {return SNew(STextBlock).Text(FText::FromString(Text)).Font(Numeric?GunsmithUI::NumberFont(Size/Scale):GunsmithUI::TextFont(Size/Scale)).ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(Wrap);}
    TSharedRef<STextBlock> Paragraph(const FString& Text,float Size=14){return Label(Text,Size,false,true);}
    TSharedRef<STextBlock> Dynamic(TSharedPtr<STextBlock>& T,float Size=14,bool Wrap=false){T=Label(TEXT(""),Size,false,Wrap);return T.ToSharedRef();}
    TSharedRef<SWidget> Button(const FString& Text,TFunction<void()> Click,TFunction<bool()> Enabled=[](){return true;})
    {return SNew(SBox).MinDesiredWidth(88/Scale).HeightOverride(36/Scale)[SNew(SButton).ButtonStyle(&Buttons).HAlign(HAlign_Center).VAlign(VAlign_Center).ContentPadding(FMargin(10/Scale,0)).IsEnabled_Lambda(MoveTemp(Enabled)).OnClicked_Lambda([this,Click=MoveTemp(Click)](){Click();Refresh();return FReply::Handled();})[Label(Text)]];}
    TSharedRef<SWidget> Glass(TSharedRef<SWidget> Content)
    {return SNew(SBackgroundBlur).BlurStrength(ColdSteelUI::GlassBlurStrength).BlurRadius(ColdSteelUI::GlassBlurRadius).CornerRadius(FVector4(10/Scale)).LowQualityFallbackBrush(&Fallback)[SNew(SBorder).BorderImage(&Frame).Padding(12/Scale)[Content]];}
    TSharedRef<SWidget> PrimaryButton()
    {
        return SNew(SBox).HeightOverride(36/Scale)[SNew(SButton).ButtonStyle(&Buttons).HAlign(HAlign_Center).VAlign(VAlign_Center)
            .IsEnabled_Lambda([this](){return CanPrimary();})
            .OnClicked_Lambda([this](){Primary();Refresh();return FReply::Handled();})[Dynamic(PrimaryText,16)]];
    }
    bool CanPrimary() const
    {
        if(bConfirmClose||!Owner->PresentationReady())return false;const auto* S=Owner->System();
        if(S->State()==EWoodworkingPhase::Preview)return bCanStart;
        if(S->State()==EWoodworkingPhase::Running)return S->Mask().Metrics().Clearance>=S->Settings().RequiredClearance;
        return bBuiltResult;
    }
    void Primary()
    {
        CancelInput();if(!Owner->PresentationReady()||!Owner->EnsureStation())return;auto* S=Owner->System();
        if(S->State()==EWoodworkingPhase::Preview)
        {
            const uint64 Before=S->Mask().CutSerial();
            if(S->StartMode(EWoodworkingMode::Craft)){Canvas->ClearFeedback();Canvas->Contact(Before);Owner->BoardChanged();}
        }
        else if(S->State()==EWoodworkingPhase::Running)S->Finish();
        else if(S->State()==EWoodworkingPhase::Complete&&!S->IsPractice())S->Claim();
        else if(Owner->RestartProject()){Canvas->ClearFeedback();bQuoteDirty=true;Build();return;}
        bQuoteDirty=true;Build();
    }
    void BuildSelection()
    {
        const auto Size=ScreenSize();const float RightInset=ColdSteelUI::NavigationDrawerInset;
        const float Width=FMath::Max(1.f,FMath::Min((float(Size.X)-RightInset-12.f)*.5f,FMath::Clamp(float(Size.X)*.48f,720.f,1040.f)));
        // The management widget uses the forging tree and DPI styling directly.
        ChildSlot.HAlign(HAlign_Right).VAlign(VAlign_Fill).Padding(FMargin(12/Scale,12/Scale,(Width+RightInset)/Scale,12/Scale))
            [SNew(SBox).WidthOverride(Width/Scale).Clipping(EWidgetClipping::ClipToBounds)
                .RenderTransform_Lambda([this,Width](){return FSlateRenderTransform(Owner->ManagementSlide(Width,Scale,true));})
                [SNew(SBox).IsEnabled_Lambda([this](){return Owner->ManagementInputReady()&&!Owner->IsPreparingProject();})
                    .RenderTransform_Lambda([this,Width](){return FSlateRenderTransform(Owner->ManagementSlide(Width,Scale,false));})
                    [Owner->ManagementContent()]]];
    }
    void BuildWorkshop()
    {
        const auto Size=ScreenSize();const bool Short=Size.Y<720;
        auto Top=SNew(SVerticalBox);
        Top->AddSlot().AutoHeight()[SNew(SHorizontalBox)+SHorizontalBox::Slot().FillWidth(1)[Dynamic(Title,20)]
            +SHorizontalBox::Slot().AutoWidth().Padding(8/Scale,0)[Dynamic(Time)]
            +SHorizontalBox::Slot().AutoWidth()[Button(TEXT("结束并返回"),[this](){Owner->RequestReturnToSelection();})]];
        Top->AddSlot().AutoHeight().Padding(0,6/Scale,0,0)[Dynamic(Mode,12)];
        auto Bottom=SNew(SVerticalBox);
        Bottom->AddSlot().AutoHeight().Padding(0,0,0,6/Scale)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[Dynamic(Clearance)]
            +SHorizontalBox::Slot().FillWidth(1)[Dynamic(Integrity)]];
        Bottom->AddSlot().AutoHeight().Padding(0,0,0,6/Scale)[Dynamic(Message,12,true)];
        if(bConfirmClose)
        {
            Bottom->AddSlot().AutoHeight()[SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,8/Scale,0)[Button(TEXT("继续加工"),[this](){bConfirmClose=false;Build();})]
                +SHorizontalBox::Slot().FillWidth(1)[Button(TEXT("确认放弃"),[this](){if(bReturnToSelection)Owner->ReturnToSelection();else Owner->CloseConfirmed();})]];
        }
        else
        {
            auto Actions=SNew(SHorizontalBox);
            Actions->AddSlot().FillWidth(1)[PrimaryButton()];
            if(Owner->System()->State()==EWoodworkingPhase::Running)
                Actions->AddSlot().FillWidth(1).Padding(8/Scale,0,0,0)[SNew(SBox).HeightOverride(36/Scale)[SNew(SButton).ButtonStyle(&Buttons).HAlign(HAlign_Center).VAlign(VAlign_Center)
                    .IsEnabled_Lambda([this](){return Owner->PresentationReady();})
                    .OnClicked_Lambda([this](){ToggleCutting();return FReply::Handled();})[Dynamic(Motor)]]];
            Bottom->AddSlot().AutoHeight()[Actions];
            auto Tools=SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(6/Scale,6/Scale));
            if(!bBuiltResult)
            {
                auto Turn=[this](){return Owner->PresentationReady();};
                Tools->AddSlot()[Button(TEXT("Q 左转 1°"),[this](){Rotate(-1);},Turn)];
                Tools->AddSlot()[Button(TEXT("E 右转 1°"),[this](){Rotate(1);},Turn)];
                Tools->AddSlot()[Button(TEXT("撤销 Ctrl+Z"),[this](){Undo();},[this](){return Owner->System()->State()==EWoodworkingPhase::Running&&Owner->System()->Mask().CanUndo();})];
                Tools->AddSlot()[Button(TEXT("复位视角"),[this](){Canvas->ResetView();})];
            }
            Tools->AddSlot()[Button(TEXT("暂停并返回"),[this](){Owner->RequestClose();})];
            Bottom->AddSlot().AutoHeight().Padding(0,6/Scale,0,0)[Tools];
            if(!Short&&!bBuiltResult)Bottom->AddSlot().AutoHeight().Padding(0,6/Scale,0,0)[Paragraph(TEXT("空格切换调整/切割 · Q/E 1°，Shift+Q/E 0.25° · 红色虚线预览落刀，红色实线正在切割 · 滚轮缩放"),12)];
        }
        auto Scene=SNew(SOverlay);
        Scene->AddSlot()[Canvas.ToSharedRef()];
        Scene->AddSlot().HAlign(HAlign_Fill).VAlign(VAlign_Top).Padding(12/Scale)[Glass(Top)];
        Scene->AddSlot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(12/Scale)
            [SNew(SBox).WidthOverride(FMath::Max(1.f,FMath::Min(940.f,float(Size.X)-24))/Scale)[Glass(Bottom)]];
        Owner->SetWorkshopInsets(FMargin(20,100,20,Short?185:230));
        ChildSlot[Scene];
    }
    TWeakObjectPtr<UColdSteelWoodworkingWidget> Owner;
    TWeakObjectPtr<UColdSteelStatusModel> Model;FDelegateHandle InventoryHandle;
    TSharedPtr<SWoodworkingCanvas> Canvas;
    FButtonStyle Buttons;FSlateBrush Frame,Fallback;
    TSharedPtr<STextBlock> Title,Mode,Time,Clearance,Integrity,Message,PrimaryText,Motor;
    FString BuiltJobId;
    bool bBuiltFinished=false;
    FString QuoteReason;
    float Scale=1;double NextRefresh=0;
    FVector2D AvailablePixels=FVector2D::ZeroVector;
    bool bConfirmClose=false,bReturnToSelection=false,bBuiltResult=false,bQuoteDirty=true,bCanStart=false;
};
