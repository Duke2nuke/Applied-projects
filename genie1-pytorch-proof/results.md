# GENIE1 local proof — measured results

Run 11 Nov 2026, CPU (4 shared cores), PyTorch 2.15.0+cpu, seed 42.
All numbers are held-out test-set metrics from `outputs/*_metrics.json`.
Nothing here is a GENIE1 submission result: the image tasks use synthetic
data and the graph tasks use JetNet, not the real test dataset.

## Task 1 — autoencoder (synthetic 125x125x3, split 800/200/200)

| Split | MSE (log1p + standardised pixels) | Tracks | ECAL | HCAL |
|---|---|---|---|---|
| Train | 0.0091 | 0.0141 | 0.0070 | 0.0063 |
| Val | 0.0095 | 0.0147 | 0.0073 | 0.0063 |
| Test | **0.0090** | 0.0138 | 0.0069 | 0.0062 |

Figure: `outputs/reconstruction.png` (2 test jets x 3 channels, orig vs recon).
Reconstructions match position/width per channel; fine speckle is smoothed.

## Image CNN baseline (synthetic, same split)

| Metric | Test |
|---|---|
| Accuracy | 0.845 |
| ROC-AUC | 0.933 |
| Precision | 0.963 |
| Recall | 0.738 |
| F1 | 0.836 |
| Confusion matrix [[TN, FP], [FN, TP]] | [[90, 3], [28, 79]] |

Val accuracy by epoch: 0.62, 0.745, 0.755, 0.815, 0.845, 0.82, 0.77, 0.82.

## Task 2 — GNN classifier (real JetNet, split 2800/600/600)

| Metric | Test |
|---|---|
| Accuracy | 0.715 |
| ROC-AUC | 0.792 |
| Precision | 0.642 |
| Recall | 0.859 |
| F1 | 0.735 |
| Confusion matrix | [[192, 132], [39, 237]] |

Val accuracy by epoch: 0.667, 0.725, 0.725, 0.702, 0.725, 0.737, 0.738, 0.732.
Note the gluon bias: 132 of 324 test quarks called gluon.

## Specific Task 1 — contrastive + linear probe (real JetNet, same split)

Method: NT-Xent tau=0.2, node-dropout views p=0.2, 6 epochs, frozen
encoder + logistic-regression probe on 64-d embeddings.

| Metric | Test |
|---|---|
| Accuracy | 0.707 |
| ROC-AUC | 0.789 |
| Precision | 0.637 |
| Recall | 0.841 |
| F1 | 0.725 |
| Confusion matrix | [[192, 132], [44, 232]] |

Contrastive loss by epoch: 4.67, 4.43, 4.33, 4.25, 4.03, 3.79.
**Verdict: does NOT beat the GNN baseline (AUC 0.789 vs 0.792).**
Documented, not hidden. Suspected causes: too few epochs, node dropout
removing the multiplicity signal, frozen probe vs end-to-end head.

## Bugs fixed during the build (honest log)

1. AE shape bug: encoder output is 64x15x15, not 64x16x16; decoder
   retuned to land exactly on 125x125 (final transposed conv k=7, s=2).
2. GNN gather bug: `Tensor.gather` needs same-ndim index; replaced with
   flat advanced indexing.
3. Synthetic generator, v1: non-overlapping widths + unnormalised kernels
   made classes trivially separable (CNN ROC-AUC 1.0, val acc 1.0 by
   epoch 2) and gluon jets 5x brighter. Fixed with overlapping width
   ranges and per-jet total-energy normalisation; re-ran everything.
   The v1 numbers were discarded, not reported as results.
