# Model strategy

## Recommended production ensemble

### 1. Defect localization: YOLO11-Seg

Use segmentation rather than only image-level classification when annotated polygon masks are available. It provides defect location and affected-area percentage, which are directly useful for severity and explanations. Start with `yolo11s-seg` for a practical accuracy/speed balance; benchmark `n` on low-power hardware and `m` on a GPU server.

### 2. Image-level quality/disease classification: EfficientNetV2-S

EfficientNetV2-S is the primary transfer-learning classifier because it offers strong feature quality at moderate compute. The training script also supports DenseNet169, which should be benchmarked because dense feature reuse can work well on fine surface textures, and MobileNetV3 for edge deployment.

### 3. Classical computer vision

Size uniformity, contour solidity, aspect ratio, exposure, sharpness, greening ratio and texture response remain explicit measured features. They provide useful grading signals and a fallback even before a local model is trained.

### 4. Price forecasting: LightGBM

For sparse mandi histories, lag/rolling/calendar features with LightGBM are easier to validate than an LSTM and often more data-efficient. The runtime keeps an auditable linear trend plus weekly residual fallback until enough history is available.

### 5. Recommendation: constrained economic scoring

The application uses explicit calculations rather than an LLM. Hard commercial constraints, expected profit and risk are inspectable. Once sufficient outcome feedback exists, a learned ranking or calibrated loss model can be introduced and explained with SHAP.

## Evaluation protocol

- Split by farm/date or capture session, not random near-duplicate images.
- Keep a genuinely unseen test set.
- Report class-wise precision, recall and F1, macro-F1, confusion matrix and calibration.
- For segmentation, report mAP50-95, precision/recall and mask IoU/Dice by defect.
- Measure inference time on the intended deployment hardware.
- For price models, use chronological back-testing and report MAE, RMSE and MAPE.
- For recommendations, compare predicted versus actual realization and pathway regret.

## Explainability

- CV overlays show the exact colour/texture/edge regions measured by the baseline.
- Grad-CAM is generated from the full classifier checkpoint.
- Segmentation masks provide direct defect-area explanations.
- Deterministic decision factors give exact contributions; SHAP is reserved for a learned estimator.
