# Phase 3 — Source / Search Universe and Custody

Epoch: `SC900-RDAF-EPOCH-2026-09-10-001`  
Observation/research cutoff: 2026-09-10  
Search mode: **targeted high-quality**, not a claimed exhaustive database dump. Saturation is **not** claimed.

## SOURCE_UNIVERSE_POLICY (applied)

See `01-epoch-freeze.md`. Consequential claims require peer-reviewed primary studies, systematic reviews, meta-analyses, major psychometrics, or official standards. No copyrighted PDFs stored in-repo.

## Search families executed (Route A and Route B used different query intents)

Discovery surfaces: Crossref/DOI resolver, ERIC, PubMed, publisher pages, author PDFs, JEDM, APA PsycNet.

Route A intents: retrieval practice / testing effect meta-analysis; spacing / distributed practice; feedback timing; transfer of test-enhanced learning; ITS effectiveness; CAT/IRT foundations; calibration metrics.

Route B intents: interleaving boundary conditions / negative effects; DKT vs simple models; learner-model evaluation inflation; item exposure; rapid guessing; gamification instability; delayed vs immediate feedback conflicts.

## Custody log (this epoch)

| Time (local) | Query intent | Route | Notable hits used |
| --- | --- | --- | --- |
| 2026-09-10 | Adesope 2017 practice testing meta | A | DOI 10.3102/0034654316689306 |
| 2026-09-10 | Brunmair & Richter 2019 interleaving meta | A/B | DOI 10.1037/bul0000209 |
| 2026-09-10 | Gervet et al. 2020 DKT vs simple KT | B | JEDM 12(3) |
| 2026-09-10 | Cepeda et al. 2006 distributed practice | A | DOI 10.1037/0033-2909.132.3.354 PMID 16719566 |
| 2026-09-10 | Kulik & Kulik 1988 feedback timing | A/B | DOI 10.3102/00346543058001079 |
| 2026-09-10 | Sailer & Homner 2020 gamification meta | A/B | DOI 10.1007/s10648-019-09498-w |
| 2026-09-10 | Wise & Kong 2005 response time effort | B | DOI 10.1207/s15324818ame1802_2 |
| 2026-09-10 | van der Linden / Stocking-Lewis CAT exposure | A/B | CAT theory & practice 2000; JEBS papers |
| 2026-09-10 | Pelánek 2017 learner modeling overview | B | DOI 10.1007/s11257-017-9193-2 |
| 2026-09-10 | Pan & Rickard 2018 transfer of TEL | A/B | DOI 10.1037/bul0000151 PMID 29733621 |

Additional **foundational** sources used from established literature identity (not re-fetched as PDFs this epoch; cited by standard bibliographic identity):

Roediger & Karpicke 2006; Rowland 2014; Dunlosky et al. 2013; Bjork desirable difficulties; Pashler et al. 2005 feedback; Butler, Karpicke, Roediger 2008; AERA/APA/NCME *Standards for Educational and Psychological Testing* 2014; Lord CAT; Hambleton IRT; Corbett & Anderson 1995 BKT; Piech et al. 2015 DKT; Khajah et al. 2016; Xiong et al. 2016; Wilson et al. 2016 IRT vs DKT; Guo et al. 2017 ECE; Brier 1950; Barnett & Ceci 2002 transfer taxonomy; Rawson & Dunlosky successive relearning; Agarwal et al. 2021 classroom retrieval review; VanLehn 2011 ITS; Koedinger et al. cognitive tutors; Settles & Meeder 2016 half-life regression; SM-2 / FSRS as scheduler family (practitioner, weaker as science); Mekler et al. 2017 gamification points; Deci intrinsic motivation; Schnipke & Scrams RT; Martinez MC vs constructed response; Higham / Koriat metacognition; Adesope correction 2017 as needed.

## Counts (honest)

```
SOURCES_SCREENED ≈ 55 (titles/abstracts/DOI pages/open PDFs via search)
SOURCES_INCLUDED_CONSEQUENTIAL = 28
SOURCES_TERMINOLOGY_ONLY = 8
SOURCE_QUALITY_STATE = TARGETED_HIGH_QUALITY_NOT_SATURATED
```

This is **not** a full PsycINFO/ERIC systematic review. Gate 1 asks whether serious candidates can be defined, not whether the literature is exhaustively mapped. A later epoch may run a protocolized systematic review if Gate 2 requires it.

## Generalization limits (apply to all included sources)

- Lab verbal-learning and classroom quizzes ≠ Microsoft SC-900.
- Medical-student retrieval ≠ product-name/concept MC for a vendor fundamentals exam.
- Flashcard SRS (Anki/FSRS) ≠ adaptive MC with explanations and follow-ups.
- ITS algebra datasets ≠ one local desktop learner.
- CAT programs have calibrated item pools and exposure machinery this engine lacks.
- Meta-analytic *g*/*d* are average effects across heterogeneous tasks.

## Quality labels used in Route files

- META_ANALYTIC
- FOUNDATIONAL
- REPLICATED
- RECENT
- CONTESTED
- WEAK
- CONTRADICTED (when a specific engine assumption is directly opposed)
