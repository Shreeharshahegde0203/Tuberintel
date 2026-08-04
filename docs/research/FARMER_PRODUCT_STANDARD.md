# Farmer product and interface standard

## Product principle

The system is an operational decision tool, not a demonstration dashboard. Every screen must answer one of four questions:

1. Is this batch safe and commercially acceptable?
2. What visible defects and grading evidence were found?
3. Where and when should it be sold, stored or processed?
4. What is the expected rupee outcome and uncertainty?

## Bilingual requirement

English (`en-IN`) and Kannada (`kn-IN`) are first-class languages. Translation covers:

- navigation and forms;
- camera guidance and image-quality errors;
- defects, grades and standards;
- recommendation explanations and warnings;
- mandi freshness/source labels;
- feedback and actual-outcome forms;
- downloadable reports.

Do not translate proper mandi names or potato varieties unless a verified local name exists. Numbers use Indian grouping and currency. Kannada should use natural agricultural vocabulary and be reviewed by a native speaker/agronomist before field deployment.

## Farmer usability

- minimum 16 px body text and 44–48 px touch targets;
- high contrast, visible focus states and keyboard support;
- no decorative gradients, glass effects, excessive cards or chatbot theatrics;
- a guided capture flow with examples of good/bad lighting;
- low-bandwidth mode, compressed uploads and resumable/direct-to-storage uploads;
- offline draft capture in a PWA, then sync when connected;
- confidence and data freshness shown beside each recommendation;
- an explicit "Unable to decide — ask an expert" state;
- no claim that image diagnosis replaces laboratory or expert inspection;
- voice/read-aloud support is a future field-tested enhancement, not a substitute for readable text.

## Standards engine

The grade engine should support selectable profiles rather than a hard-coded global A/B/C/D rule:

- configurable Indian buyer/processor specifications;
- UNECE FFV-52 fresh potato principles;
- USDA fresh, processing and seed potato profiles for comparison;
- custom contract tolerances by buyer.

The UI displays the selected profile, measured values, allowable tolerance and pass/fail evidence.

## Ethical and operational safeguards

- retain original and annotated images with consent and configurable retention;
- do not expose farmer identity in public model datasets;
- encrypt secrets and use signed storage URLs;
- log model version and market-data timestamp with every result;
- provide correction/feedback workflows;
- do not automatically transact or sell produce;
- clearly separate measured facts, predictions and user-entered assumptions.
