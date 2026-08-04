# Research-grade benchmark protocol

## 1. Problem decomposition

A single classifier is not sufficient. The production pipeline is split into:

1. **Image quality gate** — blur, exposure, obstruction and potato coverage.
2. **Tuber instance segmentation** — isolate each potato and calculate size/shape.
3. **Surface defect detection/segmentation** — bruising, cracks/cuts, scab, black scurf, rot, greening, sprouts and deformity.
4. **Batch aggregation and standards engine** — convert per-tuber measurements to lot-level tolerances.
5. **Commercial decision model** — combine quality, mandi price, storage, transport, processor demand and risk.
6. **Abstention/human review** — low-confidence or out-of-distribution samples must not receive a confident automated grade.

Leaf disease recognition is a separate optional module and must not be mixed into the post-harvest tuber benchmark.

## 2. Candidate models

### Segmentation/detection
- YOLO11-seg / YOLOv8-seg baseline
- RT-DETR detector baseline
- Mask R-CNN (Detectron2) research baseline
- Mask2Former where compute permits

### Classification / embeddings
- EfficientNetV2-S and EfficientNet-B3
- ConvNeXt-Tiny
- DenseNet169
- MobileNetV3-Large for edge devices
- Swin-Tiny
- DINOv2 embeddings with linear probing/fine-tuning for domain generalization

### Price and shelf-life
- Last-observation and seasonal-naive baselines
- LightGBM and XGBoost using lag/rolling/arrival/weather features
- Temporal models only after sufficient continuous history exists

No architecture is declared "best" from a paper's reported accuracy. Selection is based on the same grouped external benchmark.

## 3. Leakage-safe split

- Group by source dataset and original parent image.
- For local data, group by farm + capture session + tuber/batch ID.
- Keep all augmented variants in the same training group.
- Hold out at least one district, camera family and collection period for external testing.
- Publish a dataset-overlap report before training.

## 4. Metrics

### Classification
- macro F1 and balanced accuracy (primary)
- per-class precision/recall/F1
- Matthews correlation coefficient
- AUROC/AUPRC where meaningful
- expected calibration error and Brier score
- selective risk/coverage curve for abstention

### Detection/segmentation
- mAP50 and mAP50-95
- per-class AP
- Dice and IoU
- severe-defect false-negative rate
- surface-area estimation error

### Commercial grading
- weighted Cohen's kappa against two independent graders
- exact and adjacent-grade agreement
- lot-level tolerance accuracy
- buyer acceptance precision/recall

### Price forecast
- rolling-origin MAE and RMSE
- MASE against seasonal naive
- directional accuracy
- interval coverage

## 5. Acceptance gates

A model may be used in farmer-facing production only when:

- macro F1 >= 0.85 on the locked external tuber set;
- severe-defect recall >= 0.95 or the system abstains;
- calibration error <= 0.05 after temperature/isotonic calibration;
- weighted grading kappa >= 0.80;
- no protected district/camera subgroup has >10 percentage-point recall gap without a documented limitation;
- inference latency and memory meet the selected deployment tier;
- the model card lists dataset versions, known failure modes and intended use.

These are project gates, not claims that the current untrained model already meets them.

## 6. Evaluation reports

Each experiment must save:

- immutable config and git commit;
- data manifest hashes;
- confusion matrix and per-class tables;
- calibration and risk-coverage plots;
- external-domain results by district/camera/variety;
- inference benchmark;
- failure gallery reviewed by an agronomist;
- model card and reproducibility commands.
