// Included in RunSVCHReview. Reuses its isolated pawn/profile and real entry
// points. This is authority and source-clock coverage, not socket transport.
auto* Quick=Local->FindComponentByClass<UFPSQuickCombatComponent>();
auto* Haste=Local->FindComponentByClass<UFPSLightningHasteComponent>();
Check(Quick&&Haste,TEXT("execution components available"));
if(Quick&&Haste)
{
    uint32 CastId=1;
    for(float Rate:{1.f,1.5f})
    for(float Step:{1.f/30.f,.20f})
    {
        Quick->Cancel();Haste->FinishForRemoval();
        Model->Current=Seed;Model->Current.Stamina=150.f;
        Model->Current.bQuickCombatReserved=false;Model->CurrentPawn=Local;
        Configure(Local,Model,TEXT("false"),false,false);
        Local->WeaponState=EAKMWeaponState::Idle;Local->bIsAiming=Local->bAimHeld=false;
        Local->NextAllowedShotTime=0.;Local->SprintFireUnlockTime=0.;
        if(Rate>1.f)
        {
            FColdSteelNetCastRequest Request;Request.CastId=CastId++;Request.SkillId=TEXT("lightningHaste");
            FLightningHasteCast Spell;Spell.ActionBonus=Rate-1.f;Spell.Duration=60.f;Spell.ManaCost=0.f;
            Check(Haste->NetRelease(Local,Request,Model,Spell),TEXT("execution action haste prepared"));
        }
        const FString Label=FString::Printf(TEXT("clock rate=%.1f step=%.4f "),Rate,Step);
        const float Cost=Model->QuickCombatStaminaCost(),Before=Model->Stamina();
        const bool Started=Local->TriggerRifleStockMelee();
        Check(Started,Label+TEXT("real rifle quick-combat entry"));
        if(!Started)continue;
        Check(FMath::IsNearlyEqual(Model->Stamina(),Before-Cost,.001f),Label+TEXT("local stamina once"));
        Check(!Local->TriggerRifleStockMelee()&&FMath::IsNearlyEqual(Model->Stamina(),Before-Cost,.001f),
            Label+TEXT("busy input cannot spend twice"));
        Check(Local->GunplayAnimation->ActionClip==Local->QuickCombatAnimation,Label+TEXT("contact clip published on entry"));
        float WallAge=0.f,MaxClockError=0.f;
        while(Quick->IsOccupyingLeftHand()&&WallAge<2.f)
        {
            WallAge+=Step;
            // The commandlet does not tick a gameplay world. Move only this
            // action's start stamp so the real state updater sees its elapsed time.
            Local->WeaponActionStartedAt=World->GetTimeSeconds()-WallAge;
            Local->UpdateWeaponState(Step);
            if(Local->WeaponState!=EAKMWeaponState::QuickCombat)break;
            MaxClockError=FMath::Max(MaxClockError,FMath::Abs(Local->WeaponStateElapsed-Quick->GetActionAge()));
            Local->UpdateActionPose(0.f);
            MaxClockError=FMath::Max(MaxClockError,FMath::Abs(Local->GunplayAnimation->ActionTime-Quick->GetActionAge()));
        }
        const float Expected=Local->QuickCombatAnimation->GetPlayLength()/Rate;
        Check(MaxClockError<.0001f,Label+TEXT("pose and executor share source time"),MaxClockError);
        Check(WallAge>=Expected-.0001f&&WallAge<=Expected+Step+.0001f,
            Label+TEXT("normal and accelerated duration"),WallAge);
        Check(!Quick->IsOccupyingLeftHand()&&Local->WeaponState==EAKMWeaponState::Idle
            &&!Local->ActiveActionAnimation&&!Model->Current.bQuickCombatReserved,
            Label+TEXT("complete recovery releases pose and action"));
        Check(Local->NextAllowedShotTime<=World->GetTimeSeconds()+.0001,
            Label+TEXT("completion does not leave a future fire lock"));
    }
    Quick->Cancel();Haste->FinishForRemoval();
}

// Exercise the server's real intent and hit handlers with a remote-owned pawn.
// Damage values come from its shadow profile; no local target HP writes occur
// after seeding. Socket transport remains a separate runner.
Configure(Remote,Shadow,TEXT("angled_foregrip"),true,true);
Shadow->Current.Stamina=150.f;
PS->QuickCombatRequestSequence=PS->QuickCombatServerSequence=0;
PS->QuickCombatUntil=0.;PS->QuickCombatPawn.Reset();PS->QuickCombatTargets.Reset();
const float AuthorityCost=Shadow->QuickCombatStaminaCost(),AuthorityBefore=Shadow->Stamina();
PS->ServerQuickCombat_Implementation(1,Remote,.9f,false);
Check(PS->QuickCombatServerSequence==1&&FMath::IsNearlyEqual(Shadow->Stamina(),AuthorityBefore-AuthorityCost,.001f),
    TEXT("remote quick intent authorizes and spends server stamina"));
PS->ServerQuickCombat_Implementation(1,Remote,.9f,false);
Check(FMath::IsNearlyEqual(Shadow->Stamina(),AuthorityBefore-AuthorityCost,.001f),
    TEXT("duplicate quick intent cannot spend twice"));
auto* Victim=World->SpawnActor<ANurseZombie>(Remote->GetActorLocation()+FVector(100,0,0),FRotator::ZeroRotator);
Victim->Health=Victim->MaxHealth=100000.f;
Victim->Combat->ConfigureToughnessBar(FMonsterToughnessBarTuning());
FColdSteelNetHitReport Report;Report.Target=Victim;Report.ItemDefinition=SVCHWeaponAssets::Definition;
Report.AttackMeta=0x80;Report.QuickCombatSerial=1;Report.Flags=1<<3;
Report.AimOrigin=Remote->GetPawnViewLocation();Report.ImpactPoint=Victim->GetActorLocation();
Report.Direction=FVector::ForwardVector;Report.HitNormal=-FVector::ForwardVector;
Report.ClientFireTime=World->GetTimeSeconds();
const float BeforeHit=Victim->Health;
PS->ServerReportHit_Implementation(Report);
const float AfterHit=Victim->Health;
Check(AfterHit<BeforeHit,TEXT("remote SVCH quick hit applies authoritative damage"),BeforeHit-AfterHit);
PS->ServerReportHit_Implementation(Report);
Check(Victim->Health==AfterHit,TEXT("duplicate quick contact cannot damage twice"));
PS->ServerQuickCombat_Implementation(0,Remote,0.f,true);
Check(PS->QuickCombatServerSequence==1,TEXT("stale finish preserves accepted quick action"));
PS->ServerQuickCombat_Implementation(2,Local,.9f,false);
Check(PS->QuickCombatServerSequence==1&&PS->QuickCombatPawn.Get()==Remote,
    TEXT("different pawn cannot replace accepted quick action"));
PS->ServerQuickCombat_Implementation(1,Remote,0.f,true);
Check(!PS->QuickCombatServerSequence&&!PS->IsQuickCombatExecuting(Remote),
    TEXT("matching finish clears authority occupancy"));
PS->ServerReportHit_Implementation(Report);
Check(Victim->Health==AfterHit,TEXT("finished action cannot deal another hit"));
Shadow->Current.Stamina=0.f;
PS->ServerQuickCombat_Implementation(3,Remote,.9f,false);
Check(!PS->QuickCombatServerSequence&&Shadow->Stamina()==0.f,
    TEXT("insufficient server stamina rejects quick action"));
