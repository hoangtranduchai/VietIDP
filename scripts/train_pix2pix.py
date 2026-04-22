# -*- coding: utf-8 -*-
"""
Pix2Pix GAN Training Script (Stamp Eraser)
===========================================
Đào tạo mạng Generator (U-Net) và Discriminator (PatchGAN) để khôi phục
nét chữ đen dưới con dấu đỏ.

Chạy: python scripts/train_pix2pix.py
"""

import os
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import numpy as np
from tqdm import tqdm

from src.config import Config
from src.preprocessing.stamp_removal import UNetGenerator, PatchGANDiscriminator

# Cấu hình MLOps Optimization
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.backends.cudnn.benchmark = True # Ép xung thuật toán Convolution
torch.cuda.empty_cache()

# ==============================================================================
# PIPELINE DỮ LIỆU (DATASET)
# ==============================================================================
class PairedPatchDataset(Dataset):
    def __init__(self, root_dir, split="train"):
        self.split_dir = os.path.join(root_dir, split)
        self.image_files = [f for f in os.listdir(self.split_dir) if f.endswith(('.jpg', '.png'))]
        
        # Transform Normalize RGB -> [-1, 1] cho Tanh activation
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        img_path = os.path.join(self.split_dir, self.image_files[idx])
        # Load and split
        raw_img = Image.open(img_path).convert('RGB')
        w, h = raw_img.size
        # Left half is Noisy (Input), Right half is Clean (Target)
        noisy_img = raw_img.crop((0, 0, w//2, h))
        clean_img = raw_img.crop((w//2, 0, w, h))
        
        return self.transform(noisy_img), self.transform(clean_img)

# ==============================================================================
# QUY TRÌNH HUẤN LUYỆN
# ==============================================================================
def weights_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        nn.init.normal_(m.weight.data, 0.0, 0.02)
    elif classname.find('BatchNorm') != -1:
        nn.init.normal_(m.weight.data, 1.0, 0.02)
        nn.init.constant_(m.bias.data, 0)

def train_gan():
    dataset_dir = Config.DATA_DIR / "processed" / "pix2pix_dataset"
    if not dataset_dir.exists():
        print(f"❌ Không tìm thấy Dataset tại {dataset_dir}. Chạy generate_pix2pix_dataset.py trước!")
        return

    print("🚀 Khởi tạo MLOps Training Pipeline cho Pix2Pix GAN...")
    
    # 1. Prepare Data
    train_dataset = PairedPatchDataset(dataset_dir, split="train")
    train_loader = DataLoader(train_dataset, batch_size=Config.GAN_BATCH_SIZE, shuffle=True, pin_memory=True, num_workers=4)
    print(f"📦 Batch size: {Config.GAN_BATCH_SIZE} | Total steps/epoch: {len(train_loader)}")

    # 2. Build Models
    generator = UNetGenerator().to(device)
    discriminator = PatchGANDiscriminator().to(device)
    generator.apply(weights_init)
    discriminator.apply(weights_init)

    # 3. Optimizers & Losses
    criterion_GAN = nn.BCEWithLogitsLoss()
    criterion_L1 = nn.L1Loss()
    
    optimizer_G = optim.Adam(generator.parameters(), lr=Config.GAN_LEARNING_RATE, betas=(0.5, 0.999))
    optimizer_D = optim.Adam(discriminator.parameters(), lr=Config.GAN_LEARNING_RATE, betas=(0.5, 0.999))

    # Lưu trọng số
    out_dir = Config.MODELS_DIR / "finetuned" / "stamp_removal_gan"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 4. Vòng lặp Học (Training Loop)
    num_epochs = Config.GAN_NUM_EPOCHS
    lambda_L1 = Config.GAN_LAMBDA_L1
    
    for epoch in range(1, num_epochs + 1):
        generator.train()
        discriminator.train()
        
        loop = tqdm(train_loader, desc=f"Epoch [{epoch}/{num_epochs}]")
        for i, (noisy_img, clean_img) in enumerate(loop):
            noisy_img = noisy_img.to(device)
            clean_img = clean_img.to(device)
            
            # --- Huấn luyện Discriminator ---
            optimizer_D.zero_grad()
            # Fake/Real Tensors
            fake_clean = generator(noisy_img)
            pred_fake = discriminator(noisy_img, fake_clean.detach())
            loss_D_fake = criterion_GAN(pred_fake, torch.zeros_like(pred_fake))
            
            pred_real = discriminator(noisy_img, clean_img)
            loss_D_real = criterion_GAN(pred_real, torch.ones_like(pred_real))
            
            loss_D = (loss_D_real + loss_D_fake) * 0.5
            loss_D.backward()
            optimizer_D.step()
            
            # --- Huấn luyện Generator ---
            optimizer_G.zero_grad()
            pred_fake = discriminator(noisy_img, fake_clean)
            loss_G_GAN = criterion_GAN(pred_fake, torch.ones_like(pred_fake))
            
            loss_G_L1 = criterion_L1(fake_clean, clean_img) * lambda_L1
            loss_G = loss_G_GAN + loss_G_L1
            loss_G.backward()
            optimizer_G.step()
            
            # Cập nhật thông số log
            loop.set_postfix({"Loss D": f"{loss_D.item():.4f}", "Loss G": f"{loss_G.item():.4f}"})
            
        # Cuối mỗi epoch quan trọng tiến hành lưu lại bộ xương
        if epoch % 10 == 0 or epoch == num_epochs:
            checkpoint_path = out_dir / f"generator_ep{epoch}.pth"
            torch.save({'gen_state': generator.state_dict()}, checkpoint_path)
            print(f"💾 Đã sao lưu Checkpoint Epoch {epoch} tại {checkpoint_path}")

    # Đóng gói Model mạnh nhất
    best_path = out_dir / "best_generator.pth"
    torch.save({'gen_state': generator.state_dict()}, best_path)
    print(f"✅ Hoàn thành Kỷ nguyên Training! Mô hình chóp (SOTA) đã nằm tại: {best_path}")

if __name__ == "__main__":
    train_gan()
