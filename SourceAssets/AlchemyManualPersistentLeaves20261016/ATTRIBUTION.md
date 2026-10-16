# Fine-press manual sources and changes

The existing book exterior and page stack derive from **Magic book set** by **evildeer**, licensed **CC BY 4.0**.

- Original: https://sketchfab.com/3d-models/magic-book-set-ee1747b4d426446ba5f14bcf2aec8400
- License: https://creativecommons.org/licenses/by/4.0/

This local revision replaces the two printable leaf islands, authors curved thin sheets, woven bookmarks, small metal clasps and corner guards, and a leather spine lining. The original cover UVs and materials remain. Preserve the original attribution and this modification notice when distributing this adaptation.

The paper, textile and page-edge surfaces are authored from the included editable numerical recipes. Item pictures reuse the existing game catalog artwork and retain its provenance. No generated concept image is substituted for an actual item.

The two font files are fixed 400/600-weight instances of **Noto Serif SC**, obtained from Google Fonts, renamed **Alchemy Folio Serif** in the derived font metadata. The original font, OFL license, instantiation script and provenance receipt are included.

- Font source: https://github.com/google/fonts/tree/main/ofl/notoserifsc
- License: https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifsc/OFL.txt

No game, acceptance render or automated interaction test was run for this revision.

## Persistent leaf revision (2026-10-16)

This revision removes the fixed printable sheets from the binding and reuses the
locally authored fine paper outline as one double-sided skeletal template, adding
31 page-chain bones and generated skin weights. The page movement, pooling and
fixed-UV materials are implemented locally. Wawa Sensei's book example informed
the choice of independent double-sided skinned sheets; no third-party source code,
demo textures or web runtime was copied into the UE project.
