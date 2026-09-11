# Measurement And Missingness

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-003`

## Endpoint

Primary endpoint:

`7-day first-attempt correctness on CLEAN HELD-OUT SC-900 probe items`

A primary observation requires:

- designated PROBE membership before training;
- no non-probe exposure before scored attempt;
- first scored attempt on that exact item;
- 7-day timing window;
- valid SC-900 domain/objective metadata;
- valid persistence record.

## Missingness

Missing delayed outcomes must be `UNOBSERVED`. They are neither failures nor successes.

This is necessary because attrition can bias a one-learner local experiment. Treating missed probes as wrong punishes absence; treating them as correct rewards absence. Both distort the endpoint.

## Contamination

Any prior non-probe exposure makes the observation `CONTAMINATED`, including:

- question prompt exposure;
- answer or explanation reveal;
- same-item practice;
- same item in due/weak/coverage/follow-up/boss/session restore;
- analytics or export paths revealing answer/stem information.

Contaminated observations must be excluded from the primary endpoint and reported separately.

## Time Trend And Order Effects

A one-learner SC-900 study is vulnerable to:

- general improvement over calendar time;
- outside Microsoft Learn or exam-prep study;
- familiarity with the app and question style;
- policy order effects;
- fatigue and changing motivation.

The design needs paired or stratified objective blocks and predeclared analysis windows. Session alternation alone is not enough, because one policy can teach material later measured during another policy period.

## Champion Validity

Smart Practice has extensive software behavior, but software tests do not prove learning effectiveness.

Preserved distinctions:

- `CODE COVERAGE != SCIENTIFIC VALIDITY`
- `TEST PASSING != LEARNING EFFECTIVENESS`
- `PLAUSIBLE MODEL != CALIBRATED MODEL`
- `COMPLEXITY != INTELLIGENCE`
- `PERSONALIZATION != IMPROVED LEARNING`

## Disposition

The endpoint is appropriate, but measurement is not yet operationally protected. Gate 2 cannot close positively before contamination and missingness rules are represented in implementation-ready tests and bank structure.