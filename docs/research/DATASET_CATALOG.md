# Potato vision dataset catalogue

Last reviewed: 2026-07-17

This catalogue distinguishes **original photographs** from augmented copies. Augmented images are useful during training but must never be counted as independent evidence when splitting or reporting dataset size.

## Tuber-focused sources

| Dataset | Original images | Labels / task | Licence | Use decision |
|---|---:|---|---|---|
| PotatoCare | Reported as 10,117 | Healthy, black scurf, blackleg, blackspot bruising, brown rot, common scab, dry rot, pink rot, soft rot, miscellaneous | CC BY 4.0 | Candidate after file-count, duplicate and provenance audit. Published class totals are internally inconsistent and must be verified from files. |
| Potato Disease Recognition Dataset | 495 originals; 3,465 augmented | Healthy, blackspot bruising, soft rot, brown rot, dry rot | CC BY 4.0 | Use originals only for split creation. Augmented copies stay inside the training fold of their parent image. |
| Potato Viral Disease Dataset | 1,972 foliar + tuber images | Mosaic, PLRV, healthy leaf, PSTVD tuber, PVY tuber cracking | CC BY 4.0 | Use only tuber classes in post-harvest model; retain foliar classes for a separate crop-health module. |
| Mukaffi28 Potato Disease | 451 | Common scab, blackleg, dry rot, pink rot, black scurf, healthy, miscellaneous | MIT repository | Useful as a small external source. Audit overlap with PotatoGANs and PotatoCare before merging. |
| Comprehensive Potato Disease / PotatoGANs | Repository plus linked dataset | Classification and masks for black scurf/common scab; GAN experiments | Repository is public; verify dataset-level licence per asset | Use code and masks after provenance audit. Do not mix generated images into validation/test. |
| Hollow-heart potato dataset | About 2,024 records | Internal defect / hollow heart | Apache-2.0 dataset card | Separate internal-defect model; RGB surface images cannot reliably infer every internal defect. |

## Leaf-focused sources (not part of the post-harvest tuber benchmark)

| Dataset | Original images | Notes |
|---|---:|---|
| Potato Leaf Disease Dataset in Uncontrolled Environment | 3,076 | Valuable for field-domain disease recognition, but must be a separate leaf model. |
| PlantVillage potato subset | 2,152 | Controlled background; useful as a pretraining baseline, weak as proof of field performance. |
| Solanaceae Family Leaf Disease Dataset | 2,593 across crops | Multi-crop leaf data; do not combine with tuber quality labels. |

## Required local collection

Public sources do not adequately cover Karnataka varieties, local storage conditions, phone cameras, mandi grading or commercial acceptance. A deployable system therefore needs a local dataset with:

- potato variety and seed source;
- farm, district and harvest date;
- camera/device ID and capture session;
- lighting/background condition;
- tuber-level masks;
- defect masks and severity percentages;
- diameter/weight measurements;
- expert grade and buyer acceptance;
- storage temperature, humidity and elapsed days;
- actual sale channel and realized price.

## Recommended scale

The objective is not an arbitrary 50,000-image number. The research target is:

- **15,000–25,000 high-quality labelled tuber images** across defects and commercial grades;
- **30,000–60,000 additional unlabelled field/storage images** for self-supervised pretraining and active learning;
- at least **1,500–3,000 images in a locked external test set** collected from farms, cameras and dates absent from training;
- at least 300–500 examples for every safety-critical defect in the external test set where feasible.

Every burst/video frame must share a group ID so near-identical frames cannot leak across train, validation and test sets.

## Licence and provenance policy

1. Download only sources with an explicit redistribution/training licence.
2. Store source URL, version, licence, citation and checksum in the manifest.
3. Never redistribute a dataset whose licence permits research use but not redistribution.
4. Detect exact duplicates with SHA-256 and near duplicates with perceptual hashes/embeddings.
5. Keep synthetic and augmented images tagged and training-only.
6. Preserve attribution in model cards and reports.
