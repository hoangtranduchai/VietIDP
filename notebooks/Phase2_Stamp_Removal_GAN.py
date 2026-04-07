# -*- coding: utf-8 -*-
"""
Phase 2: Stamp Removal - Pix2Pix GAN
=====================================
Notebook chạy trên Google Colab (cần GPU).

Module "The Eye - Part 1": Xóa con dấu đỏ khỏi văn bản scan
sử dụng mạng Pix2Pix GAN (Image-to-Image Translation).

Kiến trúc:
- Generator: U-Net (Encoder-Decoder with skip connections)
- Discriminator: PatchGAN (70×70 patches)

Input: Ảnh văn bản có dấu đỏ → Output: Ảnh văn bản sạch
"""

# ==============================================================================
# CELL 1: CÀI ĐẶT & IMPORT
# ==============================================================================
# !pip install -q torch torchvision tensorboard Pillow opencv-python-headless

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import numpy as np
import cv2
import random
from datetime import datetime

# ==============================================================================
# CELL 2: CẤU HÌNH
# ==============================================================================
# --- Google Colab ---
# from google.colab import drive
# drive.mount('/content/drive')
# BASE_DIR = "/content/drive/MyDrive/OCR-LLM_Research"

# --- Local ---
BASE_DIR = r"E:\OCR-LLM_Research"

# Paths
STAMPED_DIR = os.path.join(BASE_DIR, "data/processed/stamped_images")
CLEAN_DIR = os.path.join(BASE_DIR, "data/processed/clean_images")
MODEL_DIR = os.path.join(BASE_DIR, "models/stamp_removal")
LOG_DIR = os.path.join(BASE_DIR, "logs/stamp_removal")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Hyperparameters
IMG_SIZE = 512          # Resize ảnh về 512x512 để training
BATCH_SIZE = 4          # Phù hợp với 8GB VRAM
NUM_EPOCHS = 100
LR = 2e-4
BETA1 = 0.5
LAMBDA_L1 = 100        # Weight cho L1 loss
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print(f"✅ Device: {DEVICE}")
if torch.cuda.is_available():
    print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
    print(f"✅ VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")


# ==============================================================================
# CELL 3: DATASET
# ==============================================================================
class StampRemovalDataset(Dataset):
    """
    Dataset cho Pix2Pix: cặp {ảnh có dấu} → {ảnh sạch}.

    Load cặp ảnh cùng tên từ 2 thư mục stamped/ và clean/.
    Áp dụng augmentation: random crop, flip, color jitter.
    """

    def __init__(self, stamped_dir, clean_dir, img_size=512, is_train=True):
        self.stamped_dir = stamped_dir
        self.clean_dir = clean_dir
        self.img_size = img_size
        self.is_train = is_train

        # Tìm cặp ảnh matching (cùng tên file)
        stamped_files = set(os.listdir(stamped_dir))
        clean_files = set(os.listdir(clean_dir))
        self.pairs = sorted(stamped_files & clean_files)

        print(f"  📦 Found {len(self.pairs)} image pairs")

        # Transforms
        self.transform = transforms.Compose([
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        filename = self.pairs[idx]

        # Load images
        stamped = Image.open(os.path.join(self.stamped_dir, filename)).convert('RGB')
        clean = Image.open(os.path.join(self.clean_dir, filename)).convert('RGB')

        # Data augmentation (training only)
        if self.is_train:
            # Random horizontal flip
            if random.random() > 0.5:
                stamped = stamped.transpose(Image.FLIP_LEFT_RIGHT)
                clean = clean.transpose(Image.FLIP_LEFT_RIGHT)

            # Random crop (crop cùng vị trí cho cả 2 ảnh)
            if random.random() > 0.3:
                i, j, h, w = transforms.RandomCrop.get_params(
                    stamped, output_size=(int(stamped.height * 0.8),
                                         int(stamped.width * 0.8))
                )
                stamped = transforms.functional.crop(stamped, i, j, h, w)
                clean = transforms.functional.crop(clean, i, j, h, w)

        stamped = self.transform(stamped)
        clean = self.transform(clean)

        return stamped, clean


# ==============================================================================
# CELL 4: GENERATOR (U-Net)
# ==============================================================================
class UNetBlock(nn.Module):
    """Block cơ bản cho U-Net."""

    def __init__(self, in_ch, out_ch, down=True, use_dropout=False):
        super().__init__()
        if down:
            self.block = nn.Sequential(
                nn.Conv2d(in_ch, out_ch, 4, stride=2, padding=1, bias=False),
                nn.BatchNorm2d(out_ch),
                nn.LeakyReLU(0.2, inplace=True)
            )
        else:
            layers = [
                nn.ConvTranspose2d(in_ch, out_ch, 4, stride=2, padding=1, bias=False),
                nn.BatchNorm2d(out_ch),
                nn.ReLU(inplace=True)
            ]
            if use_dropout:
                layers.append(nn.Dropout(0.5))
            self.block = nn.Sequential(*layers)

    def forward(self, x):
        return self.block(x)


class UNetGenerator(nn.Module):
    """
    U-Net Generator cho Pix2Pix.

    Kiến trúc: Encoder (downsampling) → Bottleneck → Decoder (upsampling)
    Skip connections giữa encoder và decoder ở cùng cấp.

    Input: (B, 3, 512, 512) → Output: (B, 3, 512, 512)
    """

    def __init__(self, in_channels=3, out_channels=3, features=64):
        super().__init__()

        # Encoder (Downsampling)
        self.enc1 = nn.Sequential(
            nn.Conv2d(in_channels, features, 4, 2, 1),
            nn.LeakyReLU(0.2, inplace=True)
        )  # 256
        self.enc2 = UNetBlock(features, features * 2)      # 128
        self.enc3 = UNetBlock(features * 2, features * 4)   # 64
        self.enc4 = UNetBlock(features * 4, features * 8)   # 32
        self.enc5 = UNetBlock(features * 8, features * 8)   # 16
        self.enc6 = UNetBlock(features * 8, features * 8)   # 8
        self.enc7 = UNetBlock(features * 8, features * 8)   # 4

        # Bottleneck
        self.bottleneck = nn.Sequential(
            nn.Conv2d(features * 8, features * 8, 4, 2, 1),  # 2
            nn.ReLU(inplace=True)
        )

        # Decoder (Upsampling) with skip connections
        self.dec1 = UNetBlock(features * 8, features * 8, down=False, use_dropout=True)     # 4
        self.dec2 = UNetBlock(features * 16, features * 8, down=False, use_dropout=True)    # 8
        self.dec3 = UNetBlock(features * 16, features * 8, down=False, use_dropout=True)    # 16
        self.dec4 = UNetBlock(features * 16, features * 8, down=False)                      # 32
        self.dec5 = UNetBlock(features * 16, features * 4, down=False)                      # 64
        self.dec6 = UNetBlock(features * 8, features * 2, down=False)                       # 128
        self.dec7 = UNetBlock(features * 4, features, down=False)                           # 256

        # Final layer
        self.final = nn.Sequential(
            nn.ConvTranspose2d(features * 2, out_channels, 4, 2, 1),  # 512
            nn.Tanh()
        )

    def forward(self, x):
        # Encoder
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        e4 = self.enc4(e3)
        e5 = self.enc5(e4)
        e6 = self.enc6(e5)
        e7 = self.enc7(e6)

        # Bottleneck
        b = self.bottleneck(e7)

        # Decoder with skip connections
        d1 = self.dec1(b)
        d2 = self.dec2(torch.cat([d1, e7], dim=1))
        d3 = self.dec3(torch.cat([d2, e6], dim=1))
        d4 = self.dec4(torch.cat([d3, e5], dim=1))
        d5 = self.dec5(torch.cat([d4, e4], dim=1))
        d6 = self.dec6(torch.cat([d5, e3], dim=1))
        d7 = self.dec7(torch.cat([d6, e2], dim=1))

        return self.final(torch.cat([d7, e1], dim=1))


# ==============================================================================
# CELL 5: DISCRIMINATOR (PatchGAN)
# ==============================================================================
class PatchGANDiscriminator(nn.Module):
    """
    PatchGAN Discriminator (70×70 patches).

    Nhận input = concat(ảnh có dấu, ảnh sạch/giả)
    Output: Matrix NxN, mỗi giá trị = xác suất patch tương ứng là thật.

    Input: (B, 6, 512, 512) → Output: (B, 1, 30, 30)
    """

    def __init__(self, in_channels=6, features=[64, 128, 256, 512]):
        super().__init__()

        layers = []
        prev_ch = in_channels

        for i, f in enumerate(features):
            if i == 0:
                layers.append(nn.Sequential(
                    nn.Conv2d(prev_ch, f, 4, 2, 1),
                    nn.LeakyReLU(0.2, inplace=True)
                ))
            else:
                layers.append(nn.Sequential(
                    nn.Conv2d(prev_ch, f, 4, 2 if i < 3 else 1, 1, bias=False),
                    nn.BatchNorm2d(f),
                    nn.LeakyReLU(0.2, inplace=True)
                ))
            prev_ch = f

        # Final classification layer
        layers.append(nn.Conv2d(prev_ch, 1, 4, 1, 1))

        self.model = nn.Sequential(*layers)

    def forward(self, x, y):
        """x = ảnh có dấu, y = ảnh sạch (thật hoặc giả)"""
        return self.model(torch.cat([x, y], dim=1))


# ==============================================================================
# CELL 6: TRAINING
# ==============================================================================
def train_stamp_removal(num_epochs=NUM_EPOCHS, resume_from=None):
    """
    Huấn luyện Pix2Pix GAN cho stamp removal.

    Loss = GAN Loss (BCE) + L1 Loss (pixel-level reconstruction)
    """
    print("🏋️ Bắt đầu huấn luyện Stamp Removal GAN")
    print(f"   Epochs: {num_epochs}, Batch size: {BATCH_SIZE}")
    print(f"   Image size: {IMG_SIZE}x{IMG_SIZE}")
    print(f"   Device: {DEVICE}")
    print()

    # Dataset & DataLoader
    dataset = StampRemovalDataset(STAMPED_DIR, CLEAN_DIR, IMG_SIZE)
    train_size = int(0.9 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset, [train_size, val_size]
    )

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE,
                              shuffle=True, num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE,
                            shuffle=False, num_workers=2, pin_memory=True)

    print(f"  📦 Train: {train_size} pairs, Val: {val_size} pairs")

    # Models
    gen = UNetGenerator().to(DEVICE)
    disc = PatchGANDiscriminator().to(DEVICE)

    # Optimizers
    opt_gen = optim.Adam(gen.parameters(), lr=LR, betas=(BETA1, 0.999))
    opt_disc = optim.Adam(disc.parameters(), lr=LR, betas=(BETA1, 0.999))

    # Loss functions
    bce_loss = nn.BCEWithLogitsLoss()
    l1_loss = nn.L1Loss()

    # Learning rate scheduler
    scheduler_gen = optim.lr_scheduler.StepLR(opt_gen, step_size=30, gamma=0.5)
    scheduler_disc = optim.lr_scheduler.StepLR(opt_disc, step_size=30, gamma=0.5)

    # Resume from checkpoint
    start_epoch = 0
    if resume_from and os.path.exists(resume_from):
        checkpoint = torch.load(resume_from, map_location=DEVICE)
        gen.load_state_dict(checkpoint['gen_state'])
        disc.load_state_dict(checkpoint['disc_state'])
        opt_gen.load_state_dict(checkpoint['opt_gen_state'])
        opt_disc.load_state_dict(checkpoint['opt_disc_state'])
        start_epoch = checkpoint['epoch'] + 1
        print(f"  ♻️ Resumed from epoch {start_epoch}")

    # Training loop
    best_val_loss = float('inf')

    for epoch in range(start_epoch, num_epochs):
        gen.train()
        disc.train()
        epoch_g_loss = 0
        epoch_d_loss = 0

        for batch_idx, (stamped, clean) in enumerate(train_loader):
            stamped = stamped.to(DEVICE)
            clean = clean.to(DEVICE)

            # === Train Discriminator ===
            fake_clean = gen(stamped)

            # Real pair
            disc_real = disc(stamped, clean)
            loss_d_real = bce_loss(disc_real, torch.ones_like(disc_real))

            # Fake pair
            disc_fake = disc(stamped, fake_clean.detach())
            loss_d_fake = bce_loss(disc_fake, torch.zeros_like(disc_fake))

            loss_d = (loss_d_real + loss_d_fake) * 0.5

            opt_disc.zero_grad()
            loss_d.backward()
            opt_disc.step()

            # === Train Generator ===
            disc_fake = disc(stamped, fake_clean)
            loss_g_gan = bce_loss(disc_fake, torch.ones_like(disc_fake))
            loss_g_l1 = l1_loss(fake_clean, clean) * LAMBDA_L1

            loss_g = loss_g_gan + loss_g_l1

            opt_gen.zero_grad()
            loss_g.backward()
            opt_gen.step()

            epoch_g_loss += loss_g.item()
            epoch_d_loss += loss_d.item()

        scheduler_gen.step()
        scheduler_disc.step()

        # Average losses
        n_batches = len(train_loader)
        avg_g = epoch_g_loss / max(n_batches, 1)
        avg_d = epoch_d_loss / max(n_batches, 1)

        # Validation
        val_loss = validate(gen, val_loader, l1_loss)

        # Print progress
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"  Epoch [{epoch+1}/{num_epochs}] "
                  f"G_Loss: {avg_g:.4f}, D_Loss: {avg_d:.4f}, "
                  f"Val_L1: {val_loss:.4f}")

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            save_path = os.path.join(MODEL_DIR, "best_generator.pth")
            torch.save({
                'epoch': epoch,
                'gen_state': gen.state_dict(),
                'disc_state': disc.state_dict(),
                'opt_gen_state': opt_gen.state_dict(),
                'opt_disc_state': opt_disc.state_dict(),
                'val_loss': val_loss
            }, save_path)

        # Save checkpoint every 20 epochs
        if (epoch + 1) % 20 == 0:
            ckpt_path = os.path.join(MODEL_DIR, f"checkpoint_epoch{epoch+1}.pth")
            torch.save({
                'epoch': epoch,
                'gen_state': gen.state_dict(),
                'disc_state': disc.state_dict(),
                'opt_gen_state': opt_gen.state_dict(),
                'opt_disc_state': opt_disc.state_dict(),
            }, ckpt_path)

    print(f"\n✅ Training hoàn tất! Best Val L1: {best_val_loss:.4f}")
    print(f"   Model saved: {os.path.join(MODEL_DIR, 'best_generator.pth')}")


def validate(gen, val_loader, l1_loss):
    """Validate generator trên tập validation."""
    gen.eval()
    total_loss = 0
    with torch.no_grad():
        for stamped, clean in val_loader:
            stamped = stamped.to(DEVICE)
            clean = clean.to(DEVICE)
            fake_clean = gen(stamped)
            total_loss += l1_loss(fake_clean, clean).item()
    return total_loss / max(len(val_loader), 1)


# --- CHẠY TRAINING ---
# Uncomment để chạy:
# train_stamp_removal(num_epochs=100)


# ==============================================================================
# CELL 7: INFERENCE - XÓA DẤU TỪ ẢNH MỚI
# ==============================================================================
def remove_stamp(image_path, model_path=None, output_path=None):
    """
    Xóa con dấu đỏ từ ảnh văn bản.

    Args:
        image_path: Đường dẫn ảnh đầu vào (có dấu)
        model_path: Đường dẫn model (.pth)
        output_path: Đường dẫn lưu ảnh đã xóa dấu
    Returns:
        PIL Image đã xóa dấu
    """
    if model_path is None:
        model_path = os.path.join(MODEL_DIR, "best_generator.pth")
    if output_path is None:
        base = os.path.splitext(image_path)[0]
        output_path = f"{base}_cleaned.png"

    # Load model
    gen = UNetGenerator().to(DEVICE)
    checkpoint = torch.load(model_path, map_location=DEVICE)
    gen.load_state_dict(checkpoint['gen_state'])
    gen.eval()

    # Load & preprocess image
    img = Image.open(image_path).convert('RGB')
    orig_size = img.size  # (W, H)

    transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    ])

    input_tensor = transform(img).unsqueeze(0).to(DEVICE)

    # Inference
    with torch.no_grad():
        output = gen(input_tensor)

    # Post-process
    output = output.squeeze(0).cpu()
    output = output * 0.5 + 0.5  # Denormalize
    output = output.clamp(0, 1)
    output_img = transforms.ToPILImage()(output)

    # Resize back to original
    output_img = output_img.resize(orig_size, Image.LANCZOS)
    output_img.save(output_path)

    print(f"✅ Đã xóa dấu: {output_path}")
    return output_img


def batch_remove_stamps(input_dir, output_dir, model_path=None):
    """Xóa dấu hàng loạt từ thư mục ảnh."""
    os.makedirs(output_dir, exist_ok=True)

    image_files = [f for f in os.listdir(input_dir)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    print(f"🔄 Đang xóa dấu từ {len(image_files)} ảnh...")

    for i, filename in enumerate(image_files):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        try:
            remove_stamp(input_path, model_path, output_path)
        except Exception as e:
            print(f"  ⚠️ Lỗi xử lý {filename}: {e}")

        if (i + 1) % 10 == 0:
            print(f"  📄 Đã xử lý {i+1}/{len(image_files)}")

    print(f"\n✅ Hoàn tất! Kết quả: {output_dir}")


# --- CHẠY INFERENCE ---
# Uncomment để chạy:
# remove_stamp("data/test_image.png")
# batch_remove_stamps("data/processed/stamped_images", "data/processed/cleaned_images")


# ==============================================================================
# CELL 8: ĐÁNH GIÁ CHẤT LƯỢNG
# ==============================================================================
from skimage.metrics import structural_similarity as ssim  # pip install scikit-image


def evaluate_stamp_removal(clean_dir, output_dir, limit=50):
    """
    Đánh giá chất lượng xóa dấu bằng SSIM và PSNR.

    So sánh ảnh đã xóa dấu (output) với ảnh sạch gốc (ground truth).
    """
    scores = {'ssim': [], 'psnr': []}

    files = sorted(os.listdir(output_dir))[:limit]

    for filename in files:
        clean_path = os.path.join(clean_dir, filename)
        output_path = os.path.join(output_dir, filename)

        if not os.path.exists(clean_path):
            continue

        clean = cv2.imread(clean_path, cv2.IMREAD_GRAYSCALE)
        output = cv2.imread(output_path, cv2.IMREAD_GRAYSCALE)

        if clean is None or output is None:
            continue

        # Resize to same size
        h, w = min(clean.shape[0], output.shape[0]), min(clean.shape[1], output.shape[1])
        clean = cv2.resize(clean, (w, h))
        output = cv2.resize(output, (w, h))

        # SSIM
        s = ssim(clean, output)
        scores['ssim'].append(s)

        # PSNR
        mse = np.mean((clean.astype(float) - output.astype(float)) ** 2)
        if mse > 0:
            psnr = 10 * np.log10(255.0 ** 2 / mse)
            scores['psnr'].append(psnr)

    print("=" * 50)
    print("📊 STAMP REMOVAL EVALUATION")
    print("=" * 50)
    print(f"  SSIM (mean): {np.mean(scores['ssim']):.4f} ± {np.std(scores['ssim']):.4f}")
    print(f"  PSNR (mean): {np.mean(scores['psnr']):.2f} ± {np.std(scores['psnr']):.2f} dB")
    print(f"  Samples evaluated: {len(scores['ssim'])}")
    print("=" * 50)

    return scores


if __name__ == '__main__':
    print("🔴 Phase 2: Stamp Removal GAN")
    print("Chạy trên Google Colab với GPU runtime")
    print("Uncomment các cell để bắt đầu training")
