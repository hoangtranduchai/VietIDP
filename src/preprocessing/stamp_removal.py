# -*- coding: utf-8 -*-
"""
Stamp Removal Module (Pix2Pix GAN)
====================================
Xóa con dấu đỏ khỏi ảnh văn bản scan sử dụng U-Net Generator.

Kiến trúc:
- Generator: U-Net 8-level encoder-decoder với skip connections
- Input: (B, 3, 512, 512) → Output: (B, 3, 512, 512)

Nguồn: Phase2_Stamp_Removal_GAN.py + Phase5_End_to_End_Pipeline.py
"""

import os
import numpy as np
import cv2
from PIL import Image

try:
    import torch
    import torch.nn as nn
    from torchvision import transforms
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# ═══════════════════════════════════════════════════════════════════════════
# U-Net Generator Architecture
# ═══════════════════════════════════════════════════════════════════════════

if HAS_TORCH:
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
        U-Net Generator cho Pix2Pix stamp removal.

        Encoder (downsampling) → Bottleneck → Decoder (upsampling)
        Skip connections giữa encoder và decoder ở cùng cấp.
        """

        def __init__(self, in_channels=3, out_channels=3, features=64):
            super().__init__()
            # Encoder
            self.enc1 = nn.Sequential(
                nn.Conv2d(in_channels, features, 4, 2, 1),
                nn.LeakyReLU(0.2, inplace=True)
            )
            self.enc2 = UNetBlock(features, features * 2)
            self.enc3 = UNetBlock(features * 2, features * 4)
            self.enc4 = UNetBlock(features * 4, features * 8)
            self.enc5 = UNetBlock(features * 8, features * 8)
            self.enc6 = UNetBlock(features * 8, features * 8)
            self.enc7 = UNetBlock(features * 8, features * 8)

            # Bottleneck
            self.bottleneck = nn.Sequential(
                nn.Conv2d(features * 8, features * 8, 4, 2, 1),
                nn.ReLU(inplace=True)
            )

            # Decoder with skip connections
            self.dec1 = UNetBlock(features * 8, features * 8, down=False, use_dropout=True)
            self.dec2 = UNetBlock(features * 16, features * 8, down=False, use_dropout=True)
            self.dec3 = UNetBlock(features * 16, features * 8, down=False, use_dropout=True)
            self.dec4 = UNetBlock(features * 16, features * 8, down=False)
            self.dec5 = UNetBlock(features * 16, features * 4, down=False)
            self.dec6 = UNetBlock(features * 8, features * 2, down=False)
            self.dec7 = UNetBlock(features * 4, features, down=False)

            # Final layer
            self.final = nn.Sequential(
                nn.ConvTranspose2d(features * 2, out_channels, 4, 2, 1),
                nn.Tanh()
            )

        def forward(self, x):
            e1 = self.enc1(x)
            e2 = self.enc2(e1)
            e3 = self.enc3(e2)
            e4 = self.enc4(e3)
            e5 = self.enc5(e4)
            e6 = self.enc6(e5)
            e7 = self.enc7(e6)

            b = self.bottleneck(e7)

            d1 = self.dec1(b)
            d2 = self.dec2(torch.cat([d1, e7], dim=1))
            d3 = self.dec3(torch.cat([d2, e6], dim=1))
            d4 = self.dec4(torch.cat([d3, e5], dim=1))
            d5 = self.dec5(torch.cat([d4, e4], dim=1))
            d6 = self.dec6(torch.cat([d5, e3], dim=1))
            d7 = self.dec7(torch.cat([d6, e2], dim=1))

            return self.final(torch.cat([d7, e1], dim=1))

    class PatchGANDiscriminator(nn.Module):
        """PatchGAN Discriminator (70×70 patches)."""

        def __init__(self, in_channels=6, features=None):
            super().__init__()
            if features is None:
                features = [64, 128, 256, 512]

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
            layers.append(nn.Conv2d(prev_ch, 1, 4, 1, 1))
            self.model = nn.Sequential(*layers)

        def forward(self, x, y):
            return self.model(torch.cat([x, y], dim=1))


# ═══════════════════════════════════════════════════════════════════════════
# Stamp Remover (Inference Wrapper)
# ═══════════════════════════════════════════════════════════════════════════

class StampRemover:
    """
    Stamp removal inference wrapper.

    Sử dụng U-Net GAN đã train để xóa con dấu đỏ khỏi ảnh.
    """

    def __init__(self, model_path=None, img_size=512):
        self.img_size = img_size
        self.model = None

        if not HAS_TORCH:
            print("⚠️ PyTorch not installed. Stamp removal disabled.")
            return

        if model_path is None:
            from src.config import Config
            model_path = str(Config.STAMP_REMOVAL_MODEL)

        if os.path.exists(model_path):
            self._load_model(model_path)
        else:
            print(f"⚠️ Stamp removal model not found: {model_path}")

    def _load_model(self, model_path):
        """Load pre-trained generator."""
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.device = device
        self.model = UNetGenerator().to(device)
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        self.model.load_state_dict(checkpoint['gen_state'])
        self.model.eval()
        print(f"✅ Stamp removal model loaded: {model_path}")

    def remove_stamp(self, image: np.ndarray) -> np.ndarray:
        """
        Xóa con dấu đỏ từ ảnh.

        Args:
            image: BGR numpy array
        Returns:
            BGR numpy array đã xóa dấu
        """
        if self.model is None:
            return image

        transform = transforms.Compose([
            transforms.Resize((self.img_size, self.img_size)),
            transforms.ToTensor(),
            transforms.Normalize([0.5] * 3, [0.5] * 3)
        ])

        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        orig_size = pil_img.size
        input_tensor = transform(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(input_tensor)

        output = output.squeeze(0).cpu() * 0.5 + 0.5
        output = output.clamp(0, 1)
        output_img = transforms.ToPILImage()(output)
        output_img = output_img.resize(orig_size, Image.LANCZOS)

        return cv2.cvtColor(np.array(output_img), cv2.COLOR_RGB2BGR)

    @property
    def is_loaded(self) -> bool:
        return self.model is not None
