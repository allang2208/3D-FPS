// Source/FPSGAME/Building/ColdSteelDoor.cpp

void AColdSteelDoor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(GetNetMode()==NM_Client)CurrentAngle=NetSwing.Angle(GetWorld());
    ApplyAngle(DeltaSeconds);
    UpdateLeafPawnCollision();
    if(GetNetMode()!=NM_Client&&HasAuthority()&&bOpen&&AutoCloseSeconds>0.f&&FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f))
    {
        AutoCloseRemaining-=DeltaSeconds;
        if(AutoCloseRemaining<=0.f)
        {
            if(bMonsterAccess && HasLivingMonsterAtDoor())AutoCloseRemaining=1.f;
            else CloseDoor();
        }
    }
    // Native swing doors are woken by the interaction or its replicated state.
    // A closed leaf still overlapping a pawn must keep polling until it can block.
    if (GetClass() == StaticClass() && CurrentAngle == TargetAngle &&
        !(GetNetMode() != NM_Client && HasAuthority() && bOpen && AutoCloseSeconds > 0.f) &&
        (bOpen || Leaf->GetCollisionResponseToChannel(ECC_Pawn) == ECR_Block))
        SetActorTickEnabled(false);
}

void AColdSteelDoor::UpdateLeafPawnCollision()
{
    if(!Leaf)return;
    // 关着且已经静止才挡玩家；开门/关门过程中与开着时对 Pawn 放行，门可以从玩家身上扫过去。
    const bool bSettled=FMath::IsNearlyEqual(CurrentAngle,TargetAngle,.5f);
    bool bBlock=!bOpen&&bSettled;
    const bool bBlockingNow=Leaf->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block;
    // 玩家还站在门板里时先别恢复阻挡，等他离开，免得把人挤住或卡住。
    if(bBlock&&!bBlockingNow&&LeafOverlapsPawn())bBlock=false;
    if(bBlock!=bBlockingNow)
        Leaf->SetCollisionResponseToChannel(ECC_Pawn,bBlock?ECR_Block:ECR_Ignore);
    if(HasAuthority()&&ActorHasTag(TEXT("VillageStable.Assembly"))&&Leaf->CanEverAffectNavigation()!=bBlock)
        Leaf->SetCanEverAffectNavigation(bBlock);
}
