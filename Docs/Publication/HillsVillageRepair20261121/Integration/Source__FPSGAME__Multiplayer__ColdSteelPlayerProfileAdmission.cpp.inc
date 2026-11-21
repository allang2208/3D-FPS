// Source/FPSGAME/Multiplayer/ColdSteelPlayerProfileAdmission.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 246-255 | bool AColdSteelPlayerState::ApplyGuestProfile(const FColdSteelProfile& GuestProfile,bool bFromNetwork)
            // A profile sent before a host-committed wall repair still contains
            // the pre-purchase balance. Replaying it must not refund the fee.
            for(const auto& Receipt:Prev.CampfireWorldReceipts)
            {
                if(Receipt.Value>Adopted.CampfireInventoryRevision&&Receipt.Key.StartsWith(TEXT("VillageDefenses_")))
                {
                    Adopted.Souls=Prev.Souls;
                    break;
                }
            }
