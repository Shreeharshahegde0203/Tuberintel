# Research source index

This is a curated, reproducible source inventory rather than a claim that every potato paper on the internet has been found. Sources are prioritized when they provide an accessible paper, official standard, dataset card or public repository.

## Open data and code

1. PotatoCare — Mendeley Data: https://data.mendeley.com/datasets/7vm7xskfg4
2. Potato Disease Recognition Dataset — Mendeley Data: https://data.mendeley.com/datasets/pmbc875pr7/1
3. Potato Viral Disease Dataset on both Foliar and Tuber — Mendeley Data: https://data.mendeley.com/datasets/rgfhzd5mzw
4. Potato Leaf Disease Dataset in Uncontrolled Environment — Mendeley Data: https://data.mendeley.com/datasets/ptz377bwb8
5. Dataset for Potato Disease Classification — GitHub: https://github.com/Mukaffi28/Potato-Disease
6. PotatoGANs code/dataset entry — GitHub: https://github.com/Mukaffi28/ExplainableAI-PotatoGAN-Cutting-Edge-Disease-Identification-for-Potatoes
7. PlantVillage — original open plant disease corpus: https://github.com/spMohanty/PlantVillage-Dataset

## Tuber quality, defects and explainability research

1. PotatoGANs: GAN augmentation, classification, instance segmentation and XAI: https://arxiv.org/abs/2405.07332
2. A Transfer Learning-Based Method for Surface Defect Detection of Potatoes: https://arxiv.org/abs/2108.06939
3. Quality Detection of Stored Potatoes via Transfer Learning: https://arxiv.org/abs/2601.00645
4. CoRe++ 3D potato shape completion project/paper: search and verify the public project release before adding its RGB-D data to training.

## Standards

1. UNECE FFV-52 Early and Ware Potatoes: https://unece.org/sites/default/files/2021-10/52EarlyandWarePotatoes_3Sepwith%20comments.pdf
2. USDA Potatoes Grades and Standards: https://www.ams.usda.gov/grades-standards/potatoes-grades-and-standards
3. USDA Potatoes for Processing Grades and Standards: https://www.ams.usda.gov/grades-standards/potatoes-processing-grades-and-standards
4. USDA Seed Potatoes Grades and Standards: https://www.ams.usda.gov/grades-standards/seed-potatoes-grades-and-standards

## Research rules derived from the review

- Treat controlled-background leaf datasets as pretraining/baseline sources, not proof of farmer-field performance.
- Do not count augmentation as new independent evidence.
- Keep leaf diagnosis, intact-tuber surface inspection and cut/internal-defect inspection as separate tasks.
- Report external-domain performance and calibration, not headline accuracy alone.
- Use an explicit licence/provenance audit before copying any image into the unified dataset.
