# Polish flags for draft v9 (paper-polish pass)

The prose was already hedged and bounded, so the pass was light: 10 edits in `paper/main.tex`, none in the abstract. No equation, number, citation or claim was added. Four edits touch meaning or claim strength and need the author's confirmation. The other six are pure language edits and are listed after the flags.

## Meaning-adjacent edits (4 flags)

1. **"Premium priced the dollar" (two places), the most important flag.**
   - Intro: "Whether that premium priced the exchange's dollar or the coin has been argued but not tested." became "Whether that premium reflected a discount on the exchange's dollar or on the coin has been argued but not tested."
   - Contribution 1: "the reading that Bitfinex's premium priced its dollar" became "the reading that Bitfinex's premium reflected a discount on its dollar".
   - Why: "priced" as a transitive verb is non-idiomatic. Risk: the new wording commits to "discount", which is the direction the Model section defines ($u>0$ means the unit is at a discount) and the direction Flowerday et al. are said to consider ("possibly a discount on its dollar balances"). Confirm that "reflected a discount on" is the reading you mean to test.
2. **"rules out" weakened.** "rules out measurement error in $L$ as the source of the shortfall" became "argues against measurement error in $L$ as the source of the shortfall". Why: one IV estimate near one does not rule out a source of error; the text elsewhere calls the month-block interval imprecise. Risk: the result now reads as weaker support. Revert if you want the stronger verb.
3. **"clearest case" softened.** "Bitfinex is the clearest case:" became "Bitfinex is a clear case:". Why: an unqualified superlative with no comparison shown. Risk: none for the evidence, but it removes a ranking you may want.
4. **Removed "and no more".** "We read it as a won-unit wedge with some residual, and no more." became "We read it as a won-unit wedge with some residual." The limit is still stated, but the explicit disclaimer is gone. Confirm that the preceding sentence ("biased toward one by FX noise common to gaps and anchor") carries the caveat on its own.

## Pure language edits (no flag)

- "Fusion reads this as a change in value, and it reports a unit drift as a price change." became "..., so a unit drift is reported as a price change."
- "which we report plainly" became "and we say so" (repeated "plain/plainly").
- "Figure 3 is the picture to start from: look at how the daily points fall..." became "In Figure 3, the daily points fall..." (removes a reader instruction).
- "(Figure 4: look at whether any row leaves the neighbourhood of the dashed line at one)" became "(Figure 4 plots each row against the dashed line at one)". It no longer says what the reader will see; check this against the figure if you want a claim there.
- "all USDT. And two of the five planned events failed the feasibility gate." joined into one sentence.
- Earlier, in the review step (text only): abbreviations GMM, HAC and CRH expanded at first use; equation references added.

## Not changed, for the author
- Related Work mixes present and past tense for prior work; left as is.
- Sections 3 and 5 have no leading sentence; adding one needs space.
- The abstract was left untouched at 296 words.
