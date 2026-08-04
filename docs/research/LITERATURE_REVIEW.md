# Systematic research summary: potato post-harvest vision and decision intelligence

Last reviewed: 2026-07-17

## Scope

The review covers open potato tuber/leaf datasets, classification, object detection, segmentation, storage-quality prediction, shape measurement, explainability, market forecasting and official grading standards. The project's primary scope remains post-harvest tuber quality and value realization.

## Main findings

1. Much of the published potato work is **leaf disease classification on controlled backgrounds**. Very high test accuracy in that setting does not establish field or storage performance.
2. Public **tuber** datasets are smaller, class-imbalanced and often assembled from web sources. They are useful for pretraining and baselines but require duplicate/provenance audits.
3. Commercial grading needs **localization and area measurement**, so detection/instance segmentation is more appropriate than classification alone.
4. Size, shape and batch uniformity should use calibrated geometry, not only neural labels.
5. Public studies report promising results for EfficientNet/DenseNet families, YOLO variants and Detectron2, but results are not directly comparable because datasets and splits differ.
6. Synthetic GAN data can improve rare classes, but generated samples must be training-only and evaluated against real external images.
7. Storage/shelf-life models are condition-specific. Exact remaining shelf life cannot be responsibly inferred from one RGB image without storage history and environment data.
8. A farmer-facing system needs calibrated confidence, abstention, standards-based grading and actual-outcome feedback—not merely a disease name.

## Research decision

Build a hybrid system:

- DINOv2/self-supervised pretraining on a large unlabelled potato image pool;
- YOLO/Mask R-CNN benchmark for tuber and defect segmentation;
- EfficientNetV2/ConvNeXt/DenseNet/MobileNet/Swin classifier benchmark;
- OpenCV/calibrated geometry for size and shape;
- rules plus auditable economic optimization initially;
- learned recommendation model only after sufficient actual-outcome data;
- LightGBM/XGBoost price forecast after rolling-origin baseline comparison.

## Evidence limitations

The current repository includes a transparent OpenCV prototype and training infrastructure, but no research-validated learned weights. Final model claims must wait for dataset acquisition, annotation, grouped training and external validation.
