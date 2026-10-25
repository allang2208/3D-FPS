// Source/FPSGAME/Movement/FPSMeleeMovementNetwork.cpp
// Within ProcessMeleeNetworkMove; includes existing neutral momentum context, retains authority phase budget and server incoming velocity.
            ServerHammerAttackId=IsHammerSprintMove(R.Kind)?R.HammerAttackId:0;
            if(R.Kind==EFPSMeleeMove::HammerDash)Player->StopMovementForMeleeSkill();
            ServerMeleeRecoveryUntil=MoveNow+Recovery;
            ServerMeleeWindowUntil=MoveNow+.75;
        }
        if(R.Sequence!=LastServerMeleeSequence||bServerMeleeBlocked||!FMath::IsFinite(R.Distance))return;
        // Cumulative displacement recovers a dropped move without applying an
        // old/pending/new packet more than once. World collision is re-run here.
        if(IsHammerSprintMove(R.Kind)&&ServerHammerAttackId!=R.HammerAttackId)return;
        const float Limit=R.Kind==EFPSMeleeMove::Zhufeng?FMath::Min(ServerMeleeBudget,WhirlwindLimit):
            R.Kind==EFPSMeleeMove::HammerAirMomentum?0.f:IsHammerSprintMove(R.Kind)?FMath::Min(ServerMeleeBudget,HammerLimit):ServerMeleeBudget;
        const float Desired=FMath::Max(ServerMeleeDistance,FMath::Min(R.Distance,Limit));
        Distance=Desired-ServerMeleeDistance;ServerMeleeDistance=Desired;
        MomentumStart=New&&IsMeleeMomentumMove(R.Kind);
    }
    if(MomentumStart)
    {
        FVector Carry=R.Momentum;
        if(Authority)
        {
            // Retain only speed that the server's preceding locomotion earned.
            Carry=R.Kind==EFPSMeleeMove::HammerAirMomentum?FVector(Velocity.X,Velocity.Y,0.f):
                Carry.GetClampedToMaxSize(Velocity.Size2D()+1.f);
            if(R.Kind==EFPSMeleeMove::HammerAirMomentum)Player->StopMovementForMeleeSkill();
        }
        // The sword only carries momentum from the air or a queued slide jump (its grounded dash is the fixed Dash stride);
        // the kukri's sprint attack carries it from the ground too, so the server brakes the same carry as the client.
        // Server: the shadow profile's held item; owning client replaying a correction: its own kukri component.
        const auto* Shadow=Player->GetNetShadowProfile();
        const auto* Held=Shadow&&!Shadow->ActiveProductionTool()?Shadow->Equipped():nullptr;
        const auto* Kukri=Player->FindComponentByClass<UKukriWeaponComponent>();
        const bool bKukri=(Held&&ColdSteelInventory::IsOneHandedMelee(*Held))||(Kukri&&Kukri->IsEquipped());
        if(IsFalling()||PendingLaunchVelocity.Z>0.f||bKukri)BeginMeleeDashMomentum(Carry);
    }
