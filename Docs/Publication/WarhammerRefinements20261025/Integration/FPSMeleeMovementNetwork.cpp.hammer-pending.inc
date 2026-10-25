// Source/FPSGAME/Movement/FPSMeleeMovementNetwork.cpp
// Inside authority ProcessMeleeNetworkMove before accepting a new movement sequence. Requires float HammerLimit alongside existing movement budget.
        if(IsHammerSprintMove(R.Kind))
        {
            const auto* Action=Player->FindComponentByClass<UProductionToolComponent>();
            float Budget=0.f,Recovery=0.f;
            if(!Action||!Action->GetCommittedSprintMovement(R.HammerAttackId,Direction,Budget,HammerLimit,Recovery))
            {
                // An unseen attack may still arrive on the reliable channel.
                // Rejected/cancelled/old attacks must never borrow a later cast.
                if(Action&&Action->IsSprintMovementPending(R.HammerAttackId))return;
                if(New){LastServerMeleeSequence=R.Sequence;ServerMeleeKind=R.Kind;bServerMeleeBlocked=true;ClientRejectMeleeMove(R.Sequence);}
                return;
            }
        }
