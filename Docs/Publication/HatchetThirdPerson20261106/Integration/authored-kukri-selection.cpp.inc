// Selected consumer excerpts; requires the current shared authored-body host.

        const FName KukriBaseKey=KukriRecovery.Advance(D->BodyState,Dt);
        const FName DualKukriKey=FPSBodyKukriMotion::DualClip(KukriBaseKey);
        FName KukriKey=!DualKukriKey.IsNone()&&MatchingOffhandKukri&&D->Clips.FindRef(DualKukriKey)?
            DualKukriKey:KukriBaseKey;
        const bool KukriRun=KukriKey==TEXT("Kukri.FullBody.Dual.Idle")&&
            D->SprintAlpha>KINDA_SMALL_NUMBER&&D->Clips.FindRef(TEXT("Kukri.FullBody.Dual.Run"));
        if(KukriRun)KukriKey=TEXT("Kukri.FullBody.Dual.Run");
        if(KukriKey==TEXT("Pistol.KukriUppercut")&&!MatchingOffhandKukri)KukriKey=NAME_None;
        if(KukriKey==TEXT("Kukri.Hatchet.DualChop")&&!MatchingOffhandKukri)KukriKey=NAME_None;

// ...
        const bool KukriMatchedRelease=HasKukriAction&&
            ((NextSwordKey==TEXT("Kukri.FullBody.Heavy")&&SwordKey==TEXT("Kukri.FullBody.Charge"))||
             (NextSwordKey==TEXT("Kukri.FullBody.Dual.Heavy")&&SwordKey==TEXT("Kukri.FullBody.Dual.Charge"))||
             (NextSwordKey==TEXT("Kukri.Falcon.Release")&&SwordKey==TEXT("Kukri.Falcon.Charge"))||
             (NextSwordKey==TEXT("Kukri.Falcon.DualRelease")&&SwordKey==TEXT("Kukri.Falcon.DualCharge")));

// ...
            Controls.LibraryPreserveHands=HasKukriAction?FPSBodyKukriMotion::PreserveHands(D->BodyState,MatchingOffhandKukri):
                Controls.bHandAttackLibrary?FPSBodyHandAttackMotion::PreserveHands(D->BodyState):0;
            // Loaded dual skills own their complete offhand blade chain.
            // Generic offhand preservation would discard this authored motion.
            if(HasKukriAction&&!KukriCarry&&MatchingOffhandKukri&&KukriKey==DualKukriKey)
                Controls.LibraryPreserveHands=0;

// ...
            else if(HasKukriAction&&FPSBodyKukriMotion::UsesAuthoredClock(KukriKey))Sample=P;

// ...
// In the authored action branch, retain only hands owned by the library:
            Controls.ActionWristMask&=Controls.LibraryPreserveHands;Controls.bCoupledActionWrists=false;
