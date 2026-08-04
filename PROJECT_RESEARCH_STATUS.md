# TuberIntel research delivery note

The repository now contains the complete research and engineering foundation for the report-defined post-harvest potato decision system.

## Delivered in this research phase

- curated open-data and open-code source inventory;
- dataset licensing/provenance rules;
- unified tuber/defect taxonomy;
- automated acquisition for approved Git/Hugging Face sources;
- controlled manual intake paths for Mendeley releases;
- corrupt-image validation and metadata inventory;
- exact and perceptual duplicate detection;
- parent/farm/session-aware train/validation/test splitting;
- five-model classification benchmark;
- detection/segmentation, explainability and forecasting pipelines;
- external-validation and model-acceptance gates;
- standards-aware product design;
- English/Kannada professional farmer-facing application;
- PostgreSQL/Supabase and deployment infrastructure.

## Scientific position

A target of 50,000 files is not accepted as evidence by itself. Augmented copies, video bursts, web duplicates, leaf images, cut-tuber images and synthetic images cannot be counted as 50,000 independent examples of the same task. The project instead targets a traceable labelled core, a larger unlabelled pool for self-supervision, and a locked external test set.

The final architecture will be selected from benchmark evidence, not from a paper's headline accuracy. The current repository does not include fabricated model weights.
