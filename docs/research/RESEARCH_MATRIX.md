# Potato computer-vision research matrix

Last reviewed: 2026-07-17

This matrix records evidence that directly influences TuberIntel. It is intentionally broader than a list of high reported accuracies: it records sensor type, task, dataset scale, openness and the reason a result may or may not transfer to a farmer-facing post-harvest system.

## Public/open data assets

| Asset | Scope | Reported scale | Labels | Licence / access | Project use |
|---|---|---:|---|---|---|
| PotatoCare | Intact/cut tuber disease images compiled from multiple sources | 10,117 reported | black scurf, blackleg, blackspot bruising, brown rot, common scab, dry rot, healthy, miscellaneous, pink rot, soft rot | CC BY 4.0, Mendeley | Largest reviewed tuber-labelled source. Use after duplicate, provenance and class-count audit; do not trust the published total without inspecting files. |
| Potato Disease Recognition Dataset | Tuber disease classification | 495 original; 3,465 augmented | healthy, blackspot bruising, soft rot, brown rot, dry rot | CC BY 4.0, Mendeley | Use originals as independent samples. Keep every augmentation in the training fold of its parent. |
| Potato Viral Disease Dataset on both Foliar and Tuber | Mixed leaf and tuber | 1,972 | mosaic/PLRV leaf, healthy leaf, PSTVD tuber, PVY tuber cracking | CC BY 4.0, Mendeley | Route tuber and leaf images to separate tasks. Useful for tuber cracking and viral symptoms, not commercial grading alone. |
| Potato Leaf Disease Dataset in Uncontrolled Environment | Field leaf diagnosis | 3,076 | bacteria, fungi, healthy, nematode, pest, phytophthora, virus | CC BY 4.0, Mendeley | Optional crop-health module. Valuable because smartphone images were collected in uncontrolled farm conditions; excluded from post-harvest tuber benchmark. |
| Mukaffi28/Potato-Disease | Tuber disease classification | 451 | common scab, blackleg, dry rot, pink rot, black scurf, healthy, miscellaneous | MIT repository | Small reproducible baseline and external source. Audit likely overlap with other compiled datasets. |
| CollinsW/PotatoHHData | Cut/open-tuber internal hollow-heart classification | 2,024 rows, 240 MB | healthy/defective internal appearance | Apache-2.0, Hugging Face | Separate internal-defect model. It cannot validate intact-surface inference because the potato is opened. |
| PlantVillage potato subset | Controlled-background leaf classification | about 2,152 potato leaf images | early blight, late blight, healthy | Open research corpus | Pretraining/baseline only. High controlled-background accuracy is not proof of field or tuber performance. |
| PotatoGANs assets | Tuber disease classification, instance segmentation and synthetic generation | linked repository/datasets | black scurf/common scab and related classes | Public code; asset licences require per-file verification | Reuse methodology and verified masks. Synthetic images are training-only and must be tagged. |

## Research and model evidence

| Work | Sensor / data | Models or method | Reported outcome | What we adopt | Limitation for this project |
|---|---|---|---|---|---|
| PotatoGANs (2024) | RGB potato disease images; real plus generated | CycleGAN, Pix2Pix, DenseNet169, ResNet152V2, InceptionResNetV2, Detectron2; Grad-CAM/Grad-CAM++/ScoreCAM | Synthetic-data and explainability experiments | Rare-class generation as an ablation; instance segmentation and multi-XAI comparison | Generated images do not replace independent real test data; dataset overlap/provenance must be audited. |
| Surface defect detection by deep transfer learning (2021) | RGB surface images | transfer-learned CNNs | Strong surface classification in the authors' setting | Include DenseNet/EfficientNet-style transfer learning baselines | Whole-image labels cannot measure defect area or reliably handle multiple defects. |
| Multi-type defect detection with MSI + MDDNet (2023) | 25-band multispectral images of 428 potatoes; five defect types | improved YOLOv3-tiny with Res2Net | mAP 90.26%, about 75 ms/image | Evidence that localization and spectral information matter; use YOLO/Mask R-CNN RGB baseline and preserve a future MSI tier | Uses specialized multispectral hardware and one variety/market context; result is not directly comparable with phone RGB. |
| Potato quality grading using 3D shape analysis | RGB-D/depth, 110 potatoes | machine vision/depth geometry | demonstrated size, volume and deformation grading | Optional calibrated depth/RGB-D extension; retain classical geometry for auditable size/shape | Very small dataset and special sensor. |
| Stored potato quality via transfer learning (2026) | RGB images plus weight data over 200 controlled-storage days | ResNet, VGG, DenseNet, ViT | DenseNet 98.03% sprout classification; coarser shelf-life groups above 89.83% | Benchmark sprout classification and include storage history, temperature/humidity and weight features | Controlled conditions; authors note the need for more varieties/storage conditions and exact shelf-life remains difficult. |
| Seed potato sprout detection (2025) | seed-potato images | lightweight improved YOLOv8 | real-time sprout detection focus | Include a lightweight detector for edge/mobile tier | Seed-potato sprout counting is narrower than ware-potato quality and value realization. |
| Hybrid internal defect pipeline (2025) | RGB images of potato slices | modular classification pipeline | reported defect-type classification including scab/greening/internal defects | Separate cut-tuber laboratory workflow | Destructive/open-slice workflow; cannot be silently mixed with intact-phone images. |
| Hybrid EfficientNetV2B3 + ViT potato plant diagnosis (2025) | primarily leaf imagery | CNN-transformer hybrid | high PlantVillage-style classification performance | Include EfficientNetV2 and Swin/ViT candidates in controlled benchmark | Leaf task and curated images; not evidence for commercial tuber grading. |
| Small-data in-field late-blight methodology (2024) | high-resolution field RGB | patching, deep CNN, focal loss | detects mild field symptoms in a small-data regime | Use grouped patching only for leaf module and focal/class-balanced losses | Leaf disease, not post-harvest tuber defects. |
| PotatoPestNet (2023) | pest images, eight classes | tuned InceptionV3 and other transfer models | about 91% accuracy/precision/recall/F1 | Evidence for separate pest module and rigorous imbalance evaluation | Not a tuber-quality model. |

## Standards and commercial evidence

| Standard | Relevant dimensions | Implementation decision |
|---|---|---|
| UNECE FFV-52 Early and Ware Potatoes | minimum quality, soundness, sprouts, greening, shape, scab/defect tolerances, sizing and lot tolerances | Add a configurable UNECE profile in the standards engine. Grade at lot level from measured tuber counts/weights, not only a neural class. |
| USDA Fresh Potatoes Grades and Standards | varietal similarity, firmness, cleanliness, shape, prohibited diseases/rot, damage and diameter limits | Add U.S. No. 1 / Commercial / No. 2 profiles for comparative/global deployments. |
| USDA Potatoes for Processing | processing-suitability and size requirements | Keep processing as a separate commercial pathway with its own acceptance profile and buyer quote. |
| Local buyer/mandi specification | variety, preferred size, appearance, pack, tolerance and price deductions | Treat as a versioned configurable contract. Do not claim one universal A/B/C/D rule matches every buyer. |

## Model shortlist to benchmark

### Tuber and defect localization

1. YOLO11-seg or YOLOv8-seg as the speed baseline.
2. RT-DETR as a detector baseline.
3. Mask R-CNN/Detectron2 as a high-quality instance-segmentation baseline.
4. Mask2Former where annotation volume and GPU compute justify it.

### Image-level classification and representation

1. EfficientNetV2-S.
2. ConvNeXt-Tiny.
3. DenseNet169.
4. MobileNetV3-Large for mobile/edge inference.
5. Swin-Tiny.
6. DINOv2 features with linear probing and fine-tuning for domain generalization.

### Economics and time series

1. Seasonal-naive and last-price baselines.
2. LightGBM and XGBoost with arrivals, lags, rolling statistics, variety, grade, location and weather.
3. Temporal neural networks only when a long, continuous, leakage-safe price history exists.

## Research conclusion

There is no single reviewed open dataset that supplies 50,000 independent, locally representative, fully labelled post-harvest tuber images with defect masks, physical dimensions, storage history, buyer acceptance and realized price. Combining files until a count reaches 50,000 would create misleading evidence because public datasets overlap, include augmentations, mix leaf/tuber/cut-potato tasks and have different licences.

The defensible target is a **multi-source, provenance-tracked corpus** with 15,000–25,000 high-quality labelled tuber images, 30,000–60,000 additional unlabelled local images for representation learning, and a locked 1,500–3,000-image external test set from unseen farms, camera families, varieties and dates. The system must abstain when the image or domain is outside validated coverage.
