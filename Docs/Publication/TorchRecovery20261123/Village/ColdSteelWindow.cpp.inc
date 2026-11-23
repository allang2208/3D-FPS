// Source/FPSGAME/Building/ColdSteelWindow.cpp

void AColdSteelWindow::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!HasAuthority())CurrentAngle=NetSwing.Angle(GetWorld());
    ApplyAngle(DeltaSeconds);
    UpdateLeafPawnCollision();
    if(HasAuthority()&&bOpen&&AutoCloseSeconds>0.f&&FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f))
    {
        AutoCloseRemaining-=DeltaSeconds;
        if(AutoCloseRemaining<=0.f)CloseWindow();
    }
    const bool bCanSleep = GetClass() == StaticClass() || (bUseAuthoredHinges && AutoCloseSeconds <= 0.f);
    const bool bWaitingToClose = HasAuthority() && bOpen && AutoCloseSeconds > 0.f;
    if (bCanSleep && !bWaitingToClose && CurrentAngle == TargetAngle &&
        (bOpen || LeafLeft->GetCollisionResponseToChannel(ECC_Pawn) == ECR_Block))
        SetActorTickEnabled(false);
}

void AColdSteelWindow::UpdateLeafPawnCollision()
{
    if(!LeafLeft)return;
    // 关着且已经静止才挡玩家；开窗/关窗过程中与开着时对 Pawn 放行，窗扇可以从玩家身上扫过去。
    const bool bSettled=FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f);
    bool bBlock=!bOpen&&bSettled;
    const bool bBlockingNow=LeafLeft->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block;
    // 玩家还站在窗扇里时先别恢复阻挡，等他离开，免得把人挤住或卡住。
    if(bBlock&&!bBlockingNow&&LeavesOverlapPawn())bBlock=false;
    if(bBlock!=bBlockingNow)SetLeavesPawnBlocking(bBlock);
}
