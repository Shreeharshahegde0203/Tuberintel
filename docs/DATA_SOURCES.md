# Data sources and collection plan

## Market data

The integration targets the data.gov.in “Current Daily Price of Various Commodities from Various Markets (Mandi)” resource maintained from AGMARKNET data. Store source and fetch time with every record. Market data must be checked for unit consistency, stale dates, duplicate records and missing prices before commercial use.

## Image data

Public datasets are suitable for bootstrapping disease recognition, but local collection is essential for commercial grading. Capture:

- multiple potato varieties and maturity stages;
- controlled and real farm/warehouse lighting;
- top, side and mixed-batch views;
- rulers or calibration markers when absolute size is required;
- defect polygons and severity, not only disease labels;
- outcome data such as buyer grade, accepted quantity and final price.

## Minimum annotation fields

- batch and image identifiers;
- variety, capture device and lighting setup;
- defects present and polygon masks;
- affected surface percentage and severity;
- size class, shape class, sprouting and greening;
- expert grade and intended commercial pathway;
- storage age and actual outcome when known.

## Leakage controls

Images from the same batch must not be split across training and test sets. Near-duplicate crops, augmented versions and repeated frames must remain in one split.
