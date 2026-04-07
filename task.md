# OCR-LLM Research System - Task Breakdown

## Phase 0: Environment Setup
- [x] Create project directory structure
- [x] Create [requirements.txt](file:///e:/OCR-LLM_Research/requirements.txt)
- [x] All 5 phase notebooks created for Colab

## Phase 1: Data Preparation & Synthetic Data Generation
- [x] [Phase1_Data_Preparation.py](file:///e:/OCR-LLM_Research/notebooks/Phase1_Data_Preparation.py) - stamp extractor, synthetic stamp generator, docx→image, LLM dataset builder
- [ ] Run on Colab: Extract stamps from 150 PDFs
- [ ] Run on Colab: Generate 200 synthetic stamps
- [ ] Run on Colab: Create training pairs (docx → image + stamp overlay)
- [ ] Run on Colab: Build LLM instruction dataset from 2000 docx

## Phase 2: Stamp Removal GAN (The Eye - Part 1)
- [x] [Phase2_Stamp_Removal_GAN.py](file:///e:/OCR-LLM_Research/notebooks/Phase2_Stamp_Removal_GAN.py) - Pix2Pix (U-Net + PatchGAN)
- [ ] Run on Colab: Train stamp removal GAN (~100 epochs)
- [ ] Evaluate with SSIM/PSNR

## Phase 3: OCR Engine (The Eye - Part 2)
- [x] [Phase3_OCR_Engine.py](file:///e:/OCR-LLM_Research/notebooks/Phase3_OCR_Engine.py) - PaddleOCR Vietnamese wrapper + CER/WER evaluation
- [ ] Run on Colab: Batch OCR 150 test PDFs
- [ ] Evaluate OCR accuracy

## Phase 4: LLM Fine-tuning (The Brain)
- [x] [Phase4_LLM_Finetuning.py](file:///e:/OCR-LLM_Research/notebooks/Phase4_LLM_Finetuning.py) - Qwen-2.5-7B QLoRA fine-tuning pipeline
- [ ] Run on Colab: Fine-tune Qwen on instruction dataset
- [ ] Evaluate Precision/Recall/F1

## Phase 5: End-to-End Pipeline & Web App
- [x] [Phase5_End_to_End_Pipeline.py](file:///e:/OCR-LLM_Research/notebooks/Phase5_End_to_End_Pipeline.py) - Full pipeline + FastAPI
- [ ] Run end-to-end test on sample PDFs
- [ ] Deploy API server

## Phase 6: Evaluation & Report
- [ ] Run comprehensive benchmarks on 150 test PDFs
- [ ] Generate performance report
- [ ] Create walkthrough document
