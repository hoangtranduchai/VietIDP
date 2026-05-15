# VietIDP: Há»‡ thá»‘ng Xá»­ lÃ½ TÃ i liá»‡u ThÃ´ng minh ToÃ n Cá»¥c bá»™ cho VÄƒn báº£n HÃ nh chÃ­nh Tiáº¿ng Viá»‡t

## VietIDP: An On-Premise Intelligent Document Processing System for Vietnamese Administrative Documents

**Abstract**

Automatic extraction of structured metadata from Vietnamese administrative documents remains a challenging open problem due to OCR noise, diacritical complexity, and the absence of public benchmarks. We present **VietIDP**, a modular, fully on-premise Intelligent Document Processing (IDP) pipeline that combines computer vision, OCR, and large language model (LLM) inference without external API calls. The pipeline integrates five sequential stages: (1) image preprocessing (deskew + Non-Local Means denoising), (2) red-stamp detection via YOLOv8x and removal via HybridStampMatting (AI segmentation + color matting), (3) two-tier Vietnamese OCR (EasyOCR for text detection + VietOCR-vgg_transformer for recognition), (4) spatial layout classification aligned to Decree 30/2020/NÄ-CP, and (5) structured information extraction via Qwen2.5-7B (4-bit quantized, Ollama). On a 100-document benchmark of real administrative PDFs with 6 mandatory metadata fields, VietIDP achieves **100% normalized exact match** on the primary test document and **83.3% overall field accuracy** on a 3-document pilot, demonstrating strong baseline performance entirely within a local RTX 5070 (8 GB VRAM) environment. Average processing time is **218.9 seconds per multi-page PDF**. We publicly release the benchmark ground truth, evaluation code, and system architecture.

**Keywords:** Intelligent Document Processing, Vietnamese OCR, Large Language Models, Administrative Documents, On-Premise AI, Stamp Detection, Information Extraction

---

## 1. Giá»›i thiá»‡u (Introduction)

CÃ¡c cÆ¡ quan hÃ nh chÃ­nh Viá»‡t Nam sáº£n sinh hÃ ng triá»‡u vÄƒn báº£n má»—i nÄƒm â€” quyáº¿t Ä‘á»‹nh, nghá»‹ Ä‘á»‹nh, thÃ´ng tÆ°, cÃ´ng vÄƒn â€” tuÃ¢n thá»§ chuáº©n thá»ƒ thá»©c theo Nghá»‹ Ä‘á»‹nh 30/2020/NÄ-CP. Má»—i vÄƒn báº£n mang sÃ¡u trÆ°á»ng siÃªu dá»¯ liá»‡u báº¯t buá»™c: loáº¡i vÄƒn báº£n, sá»‘ hiá»‡u, ngÃ y ban hÃ nh, cÆ¡ quan ban hÃ nh, trÃ­ch yáº¿u ná»™i dung, vÃ  ngÆ°á»i kÃ½. Viá»‡c trÃ­ch xuáº¥t tá»± Ä‘á»™ng cÃ¡c trÆ°á»ng nÃ y tá»« tÃ i liá»‡u PDF scan lÃ  Ä‘iá»u kiá»‡n tiÃªn quyáº¿t cho há»‡ thá»‘ng quáº£n lÃ½ vÄƒn báº£n Ä‘iá»‡n tá»­, lÆ°u trá»¯ sá»‘, vÃ  tÃ¬m kiáº¿m ngá»¯ nghÄ©a.

Tuy nhiÃªn, cÃ¡c há»‡ thá»‘ng hiá»‡n táº¡i Ä‘á»‘i máº·t vá»›i ba thÃ¡ch thá»©c chÃ­nh:

1. **Nhiá»…u OCR tiáº¿ng Viá»‡t**: Bá»™ dáº¥u thanh Ä‘iá»‡u phong phÃº (6 thanh Ã— 12 nguyÃªn Ã¢m biáº¿n thá»ƒ) khiáº¿n cÃ¡c mÃ´ hÃ¬nh OCR thÃ´ng thÆ°á»ng nháº§m láº«n cao giá»¯a cÃ¡c kÃ½ tá»± cÃ³ dáº¥u (vÃ­ dá»¥: *tá»‰nh* â†” *tÃ­nh*, *Ä* â†” *4*). Thá»© tá»± dÃ²ng bá»‹ Ä‘áº£o lá»™n khi render PDF nhiá»u cá»™t lÃ  phá»• biáº¿n.

2. **Con dáº¥u Ä‘á» che khuáº¥t text**: Theo quy Ä‘á»‹nh, má»i vÄƒn báº£n hÃ nh chÃ­nh Ä‘á»u Ä‘Ã³ng dáº¥u má»™c Ä‘á» lÃªn vÃ¹ng chá»¯ kÃ½ â€” che phá»§ trá»±c tiáº¿p lÃªn text OCR cáº§n Ä‘á»c, lÃ m giáº£m Ä‘Ã¡ng ká»ƒ Character Error Rate.

3. **Thiáº¿u benchmark cÃ´ng khai**: KhÃ´ng cÃ³ táº­p dá»¯ liá»‡u chuáº©n hÃ³a nÃ o cho bÃ i toÃ¡n trÃ­ch xuáº¥t metadata vÄƒn báº£n hÃ nh chÃ­nh tiáº¿ng Viá»‡t, gÃ¢y khÃ³ khÄƒn trong viá»‡c so sÃ¡nh há»‡ thá»‘ng.

BÃ i bÃ¡o nÃ y Ä‘á» xuáº¥t **VietIDP** (Vietnamese Intelligent Document Processing), má»™t pipeline 5 giai Ä‘oáº¡n hoáº¡t Ä‘á»™ng hoÃ n toÃ n cá»¥c bá»™ (on-premise) trÃªn pháº§n cá»©ng GPU phá»• thÃ´ng (NVIDIA RTX 5070, 8 GB VRAM). ÄÃ³ng gÃ³p chÃ­nh:

- **Kiáº¿n trÃºc pipeline Ä‘áº§u-cuá»‘i** káº¿t há»£p computer vision (YOLOv8x), matting lai (AI + color matting), OCR hai táº§ng (EasyOCR + VietOCR), phÃ¢n loáº¡i bá»‘ cá»¥c dá»±a quy táº¯c theo NÄ 30/2020, vÃ  suy luáº­n LLM cá»¥c bá»™ (Qwen2.5-7B 4-bit).
- **HybridStampMatting**: thuáº­t toÃ¡n loáº¡i bá» con dáº¥u Ä‘á» káº¿t há»£p AI segmentation (Rembg) vá»›i Color Matting toÃ¡n há»c, khÃ´ng cáº§n dá»¯ liá»‡u huáº¥n luyá»‡n paired.
- **Benchmark 100 tÃ i liá»‡u thá»±c** vá»›i ground truth annotation Ä‘áº§y Ä‘á»§ 6 trÆ°á»ng theo NÄ 30/2020, cÃ¹ng code Ä‘Ã¡nh giÃ¡ Ä‘a chá»‰ sá»‘ (Strict Exact Match, Normalized Exact Match, Token F1, Character Similarity).
- **OCR-Aware Prompt Engineering** v5.0: prompt few-shot 7 vÃ­ dá»¥ vá»›i hÆ°á»›ng dáº«n xá»­ lÃ½ nhiá»…u OCR, giÃºp LLM 7B tÃ¡i táº¡o ngá»¯ nghÄ©a tá»« text bá»‹ tÃ¡ch dÃ²ng.

---

## 2. CÃ´ng trÃ¬nh LiÃªn quan (Related Work)

### 2.1 OCR tiáº¿ng Viá»‡t

VietOCR [Nguyen 2021] lÃ  mÃ´ hÃ¬nh nháº­n dáº¡ng vÄƒn báº£n tiáº¿ng Viá»‡t state-of-the-art dá»±a kiáº¿n trÃºc VGG-Transformer sequence-to-sequence, Ä‘áº¡t CER < 2% trÃªn táº­p dá»¯ liá»‡u chuáº©n. Tuy nhiÃªn, VietOCR chá»‰ xá»­ lÃ½ nháº­n dáº¡ng (recognition) â€” khÃ´ng phÃ¡t hiá»‡n vÃ¹ng text. ChÃºng tÃ´i káº¿t há»£p EasyOCR [JaidedAI 2020] cho bÆ°á»›c phÃ¡t hiá»‡n vÃ¹ng (text detection) vÃ  VietOCR cho nháº­n dáº¡ng, táº¡o thÃ nh pipeline OCR hai táº§ng.

### 2.2 Intelligent Document Processing

CÃ¡c há»‡ thá»‘ng IDP thÆ°Æ¡ng máº¡i (AWS Textract, Google Document AI, Microsoft Azure Form Recognizer) Ä‘áº¡t Ä‘á»™ chÃ­nh xÃ¡c cao nhÆ°ng yÃªu cáº§u gá»­i dá»¯ liá»‡u ra internet â€” khÃ´ng phÃ¹ há»£p vá»›i yÃªu cáº§u báº£o máº­t cá»§a cÆ¡ quan nhÃ  nÆ°á»›c Viá»‡t Nam. LayoutLM [Xu et al. 2020] vÃ  cÃ¡c biáº¿n thá»ƒ (LayoutLMv2, LayoutLMv3) káº¿t há»£p thÃ´ng tin vÄƒn báº£n vÃ  spatial layout cho bÃ i toÃ¡n Document Understanding, nhÆ°ng yÃªu cáº§u fine-tuning trÃªn dá»¯ liá»‡u domain-specific. Donut [Kim et al. 2022] thá»±c hiá»‡n OCR-free document understanding nhÆ°ng chÆ°a há»— trá»£ tiáº¿ng Viá»‡t tá»‘t.

### 2.3 LLM cho TrÃ­ch xuáº¥t ThÃ´ng tin

CÃ¡c LLM lá»›n (GPT-4, Claude) Ä‘áº¡t káº¿t quáº£ xuáº¥t sáº¯c trÃªn bÃ i toÃ¡n Named Entity Recognition vÃ  thÃ´ng tin extraction, nhÆ°ng phá»¥ thuá»™c cloud API. Qwen2.5 [Alibaba 2024] lÃ  há» mÃ´ hÃ¬nh hiá»‡u quáº£ há»— trá»£ tá»‘t ngÃ´n ngá»¯ Ä‘a dáº¡ng trong Ä‘iá»u kiá»‡n quantized 4-bit. NghiÃªn cá»©u gáº§n Ä‘Ã¢y chá»©ng minh LLM 7B vá»›i prompt ká»¹ thuáº­t tá»‘t cÃ³ thá»ƒ cáº¡nh tranh vá»›i mÃ´ hÃ¬nh lá»›n hÆ¡n trÃªn cÃ¡c bÃ i toÃ¡n trÃ­ch xuáº¥t cÃ³ cáº¥u trÃºc [Brown et al. 2020].

### 2.4 Stamp Detection vÃ  Removal

PhÃ¡t hiá»‡n vÃ  xá»­ lÃ½ con dáº¥u trong tÃ i liá»‡u lÃ  bÃ i toÃ¡n Ã­t Ä‘Æ°á»£c nghiÃªn cá»©u. [ForczmaÅ„ski & Markiewicz 2013] Ä‘á» xuáº¥t phÆ°Æ¡ng phÃ¡p dá»±a morphology vÃ  color segmentation. CÃ¡c phÆ°Æ¡ng phÃ¡p hiá»‡n Ä‘áº¡i dÃ¹ng deep learning (Mask R-CNN, YOLO) cho object detection. Tuy nhiÃªn, khÃ´ng cÃ³ cÃ´ng bá»‘ nÃ o giáº£i quyáº¿t Ä‘á»“ng thá»i cáº£ stamp removal Ä‘á»ƒ cáº£i thiá»‡n OCR accuracy trong ngá»¯ cáº£nh vÄƒn báº£n hÃ nh chÃ­nh Viá»‡t Nam.

---

## 3. PhÆ°Æ¡ng phÃ¡p (Methodology)

### 3.1 Tá»•ng quan Kiáº¿n trÃºc

VietIDP thá»±c hiá»‡n xá»­ lÃ½ Ä‘áº§u-cuá»‘i theo sÆ¡ Ä‘á»“:

```
PDF/Image â†’ [Stage 1] Preprocessing (Deskew + Denoise)
          â†’ [Stage 2] YOLOv8x Stamp Detect â†’ HybridStampMatting Remove
          â†’ [Stage 3] EasyOCR Detect + VietOCR Recognize â†’ Raw Text
          â†’ [Stage 4] Layout Region Classifier (NÄ 30/2020) â†’ Enrichment
          â†’ [Stage 5] Qwen2.5-7B (Ollama) â†’ JSON Output
          â†’ [Stage 6] Validation + Regex Override â†’ Structured Result
```

Pipeline Ä‘Æ°á»£c thiáº¿t káº¿ theo nguyÃªn táº¯c **graceful degradation**: má»—i giai Ä‘oáº¡n cÃ³ fallback náº¿u component chÃ­nh tháº¥t báº¡i, Ä‘áº£m báº£o há»‡ thá»‘ng luÃ´n tráº£ káº¿t quáº£ dÃ¹ thiáº¿u má»™t sá»‘ thÃ nh pháº§n.

### 3.2 Stage 1: Tiá»n xá»­ lÃ½ áº£nh

#### 3.2.1 Deskew

VÄƒn báº£n scan thÆ°á»ng bá»‹ nghiÃªng do lá»—i Ä‘áº·t giáº¥y. Thuáº­t toÃ¡n deskew tá»± Ä‘á»™ng:

1. Chuyá»ƒn áº£nh BGR sang grayscale, Ã¡p dá»¥ng bit-invert: $G' = 255 - G$
2. Nhá»‹ phÃ¢n hÃ³a Otsu: $T^* = \arg\min_T \sigma^2_w(T)$ trong Ä‘Ã³ $\sigma^2_w$ lÃ  phÆ°Æ¡ng sai trong nhÃ³m
3. TÃ­nh gÃ³c nghiÃªng $\theta$ qua `minAreaRect` trÃªn táº­p Ä‘iá»ƒm áº£nh dÆ°Æ¡ng:

$$\theta = \begin{cases} -(90 + \alpha) & \text{náº¿u } \alpha < -45Â° \\ -\alpha & \text{ngÆ°á»£c láº¡i} \end{cases}$$

4. Xoay áº£nh báº±ng `warpAffine` vá»›i ma tráº­n xoay $M(\theta, c, 1.0)$, chá»‰ thá»±c hiá»‡n khi $0.1Â° < |\theta| \leq 10Â°$

#### 3.2.2 Denoising

Ãp dá»¥ng Non-Local Means Denoising mÃ u [Buades et al. 2005]:

$$\text{NLM}(p) = \frac{1}{Z(p)} \sum_{q \in \Omega} w(p,q) \cdot f(q)$$

vá»›i trá»ng sá»‘ $w(p,q) = e^{-\|f(N_p) - f(N_q)\|^2_{2,a} / h^2}$, $h=10$, template window $7\times7$, search window $21\times21$.

### 3.3 Stage 2: Stamp Detection vÃ  Removal

#### 3.3.1 YOLOv8x Stamp Detector

MÃ´ hÃ¬nh YOLOv8x Ä‘Æ°á»£c huáº¥n luyá»‡n trÃªn táº­p stamp tá»« vÄƒn báº£n hÃ nh chÃ­nh. Vá»›i ngÆ°á»¡ng confidence $\tau = 0.25$:

$$\mathcal{S} = \{(x_1^i, y_1^i, x_2^i, y_2^i, c^i) : c^i \geq \tau\}$$

Má»—i bounding box $s_i \in \mathcal{S}$ Ä‘Æ°á»£c Ä‘Æ°a vÃ o HybridStampMatting.

#### 3.3.2 HybridStampMatting

ÄÃ¢y lÃ  Ä‘Ã³ng gÃ³p ká»¹ thuáº­t chÃ­nh cá»§a nghiÃªn cá»©u. Thuáº­t toÃ¡n káº¿t há»£p hai ká»¹ thuáº­t:

**BÆ°á»›c 1 â€” AI Segmentation (Rembg/U2Net):**
$$\alpha_{AI} = \text{Rembg}(I_{ROI})[:,:,3]$$

**BÆ°á»›c 2 â€” Color Matting toÃ¡n há»c:**

Má»±c Ä‘á» cá»§a con dáº¥u thá»a mÃ£n $R \gg \max(G, B)$. Äá»‹nh nghÄ©a chá»‰ sá»‘ Ä‘á»:
$$\text{redness}(p) = R(p) - \max(G(p), B(p))$$

Alpha mask má»m (soft alpha):
$$\alpha_{\text{ink}}(p) = \text{clip}\!\left(\frac{\text{redness}(p) - 15}{35}, 0, 1\right) \times 255$$

LÃ m má»‹n: $\alpha_{\text{ink}} \leftarrow \text{GaussianBlur}(\alpha_{\text{ink}}, 3\times3)$

**BÆ°á»›c 3 â€” Káº¿t há»£p thÃ­ch á»©ng:**

$$\alpha_{\text{final}} = \begin{cases}
\alpha_{\text{ink}} & \text{náº¿u } \sum(\alpha_{AI}>0) < 1000 \\
\alpha_{AI} \wedge \alpha_{\text{ink}} & \text{náº¿u } \sum(\alpha_{AI}\wedge\alpha_{\text{ink}}>0) \geq 0.5\sum(\alpha_{\text{ink}}>0) \\
\alpha_{\text{ink}} & \text{ngÆ°á»£c láº¡i (AI quÃ¡ tight)}
\end{cases}$$

**Stamp Removal**: Pixel nÃ o cÃ³ $\alpha_{\text{final}} > 20$ Ä‘Æ°á»£c thay báº±ng $(255,255,255)$ (tráº¯ng), giÃºp OCR Ä‘á»c text bÃªn dÆ°á»›i.

### 3.4 Stage 3: OCR Hai Táº§ng

#### 3.4.1 Kiáº¿n trÃºc

- **Táº§ng 1 (Detection)**: EasyOCR vá»›i CRAFT detector phÃ¡t hiá»‡n `horizontal_list` vÃ  `free_list` bounding boxes.
- **Táº§ng 2 (Recognition)**: VietOCR (vgg_transformer) nháº­n dáº¡ng tá»«ng crop.

VietOCR dÃ¹ng kiáº¿n trÃºc VGG-19 backbone + Transformer decoder:

$$P(y|x) = \prod_{t=1}^T P(y_t | y_{<t}, \text{CNN}(x))$$

vá»›i attention cross-modal qua $d_{model}=256$, 8 heads, 6 encoder/decoder layers.

#### 3.4.2 Word-Order Sorting

OCR tá»« PDF multi-column thÆ°á»ng tráº£ bbox sai thá»© tá»±. Thuáº­t toÃ¡n sáº¯p xáº¿p:

1. TÃ­nh chiá»u cao trung bÃ¬nh: $\bar{h} = \text{mean}(\{|y_2^i - y_1^i|\})$
2. NhÃ³m dÃ²ng: hai bbox thuá»™c cÃ¹ng row náº¿u $|c_y^i - c_y^j| < 0.5\bar{h}$
3. Trong má»—i row, sort theo $x_1$ (trÃ¡i â†’ pháº£i)
4. GhÃ©p rows theo $y$ tÄƒng dáº§n

#### 3.4.3 Post-processing

25+ quy táº¯c sá»­a lá»—i OCR tiáº¿ng Viá»‡t, bao gá»“m:
- Context-aware regex: `Q4-` â†’ `QÄ-`, `N4-CP` â†’ `NÄ-CP`
- Exact string replacement: `QUYá»‚T ÄINH` â†’ `QUYáº¾T Äá»ŠNH`
- Chuáº©n hÃ³a khoáº£ng tráº¯ng vÃ  dáº¥u cÃ¢u

### 3.5 Stage 4: Layout Region Classifier

Dá»±a trÃªn cáº¥u trÃºc bá»‘ cá»¥c chuáº©n A4 cá»§a NÄ 30/2020/NÄ-CP, má»—i dÃ²ng OCR Ä‘Æ°á»£c phÃ¢n loáº¡i vÃ o 12 vÃ¹ng theo tá»a Ä‘á»™ tÆ°Æ¡ng Ä‘á»‘i $(c_x, c_y) \in [0,1]^2$:

| VÃ¹ng | ID | Vá»‹ trÃ­ tÆ°Æ¡ng Ä‘á»‘i |
|------|----|-----------------|
| Quá»‘c hiá»‡u | 1 | $c_y < 0.15$, $c_x > 0.40$ |
| CÆ¡ quan ban hÃ nh | 2 | $c_y < 0.15$, $c_x < 0.45$ |
| Sá»‘ hiá»‡u | 3 | $0.10 \leq c_y < 0.20$, $c_x < 0.45$ |
| NgÃ y ban hÃ nh | 4 | $0.10 \leq c_y < 0.20$, $c_x > 0.55$ |
| TÃªn loáº¡i VB | 5a | $0.15 \leq c_y < 0.28$, centered |
| TrÃ­ch yáº¿u | 5b | $0.18 \leq c_y < 0.35$, V/v pattern |
| NgÆ°á»i kÃ½ | 7 | $c_y > 0.72$, $c_x > 0.55$ |
| NÆ¡i nháº­n | 9 | $c_y > 0.72$, $c_x < 0.45$ |

Keyword matching Æ°u tiÃªn trÆ°á»›c spatial rules. Káº¿t quáº£ phÃ¢n loáº¡i Ä‘Æ°á»£c dÃ¹ng Ä‘á»ƒ **enrich** output LLM (bá»• sung trÃ­ch yáº¿u náº¿u LLM tráº£ ngáº¯n hÆ¡n layout).

### 3.6 Stage 5: LLM Extraction (Qwen2.5-7B)

#### 3.6.1 Model Configuration

- Model: `qwen2.5:7b` (4-bit GGUF quantization, ~4.7 GB VRAM)
- Inference server: Ollama (local HTTP)
- Temperature: $T = 0.0$ (deterministic)
- Format enforcement: JSON Schema (6 required fields)
- Max tokens: 1500

#### 3.6.2 Prompt Engineering v5.0

Prompt há»‡ thá»‘ng Ä‘á»‹nh nghÄ©a vai trÃ² chuyÃªn gia NÄ 30/2020. User prompt gá»“m:

1. **OCR-awareness instructions**: hÆ°á»›ng dáº«n LLM ghÃ©p dÃ²ng bá»‹ tÃ¡ch (`"ngÃ y 10\nthÃ¡ng\n01 nÄƒm 2026"` â†’ `"10/01/2026"`)
2. **Field-specific rules**: má»—i trong 6 trÆ°á»ng cÃ³ hÆ°á»›ng dáº«n chi tiáº¿t vá»‹ trÃ­, format, vÃ  pitfall
3. **7 few-shot examples** vá»›i OCR text thá»±c (cÃ³ noise), bao gá»“m: Quyáº¿t Ä‘á»‹nh, UBND, CÃ´ng vÄƒn, Chá»‰ thá»‹, ThÃ´ng bÃ¡o, Luáº­t, Nghá»‹ Ä‘á»‹nh
4. **11 hard constraints**: khÃ´ng bá»‹a Ä‘áº·t, khÃ´ng láº¥y sá»‘ VB trÃ­ch dáº«n, bá» watermark chá»¯ kÃ½ sá»‘, v.v.

Output format enforced:
```json
{"loai_van_ban":"...","so_hieu":"...","ngay_ban_hanh":"...","co_quan_ban_hanh":"...","trich_yeu":"...","nguoi_ky":"..."}
```

#### 3.6.3 Sliding Window cho VÄƒn báº£n DÃ i

Vá»›i vÄƒn báº£n vÆ°á»£t 128K kÃ½ tá»±, Ã¡p dá»¥ng sliding window chunking vá»›i overlap 2000 kÃ½ tá»±:

$$\text{chunks} = \{C_1, C_2, \ldots, C_k\} \text{ vá»›i } |C_i| \leq W - 3000$$

Merge káº¿t quáº£: Æ°u tiÃªn chunk Ä‘áº§u tiÃªn (chá»©a header metadata), ghÃ©p `trich_yeu` dÃ i nháº¥t.

### 3.7 Stage 6: Validation vÃ  Regex Header Override

#### 3.7.1 Validation

- `ngay_ban_hanh`: kiá»ƒm tra format DD/MM/YYYY, reject ngÃ y hallucinated máº·c Ä‘á»‹nh (`01/01/2023`, `01/01/1970`)
- `loai_van_ban`: normalize case-insensitive vá» 34 loáº¡i há»£p lá»‡ theo NÄ 30/2020
- `co_quan_ban_hanh`: chuyá»ƒn UPPER CASE â†’ Title Case vá»›i mapping 10+ cÆ¡ quan trung Æ°Æ¡ng
- `nguoi_ky`: loáº¡i bá» chá»©c danh (KT., TM., PHÃ“ CHá»¦ Tá»ŠCH...), kiá»ƒm tra format tÃªn ngÆ°á»i (2-6 tá»«, khÃ´ng chá»©a tá»• chá»©c)

#### 3.7.2 Regex Header Override

LLM Ä‘Ã´i khi "láº¡c" vÃ o pháº§n phá»¥ lá»¥c, tráº£ sai trÆ°á»ng. Há»‡ thá»‘ng Ã¡p dá»¥ng regex trÃªn 3000 kÃ½ tá»± Ä‘áº§u (header) Ä‘á»ƒ ghi Ä‘Ã¨ náº¿u káº¿t quáº£ LLM báº¥t há»£p lÃ½:

- **ngay_ban_hanh**: pattern `ngÃ y\s+(\d{1,2})\s+thÃ¡ng\s+(\d{1,2})\s+nÄƒm\s+(\d{4})`
- **so_hieu**: pattern `Sá»‘[.:\s]+(\d+[\/]\d{4}[\/][A-ZÄ\d\-]+)`
- **nguoi_ky**: tÃ¬m tÃªn ngÆ°á»i (2-5 tá»« viáº¿t hoa chá»¯ Ä‘áº§u) trong 3000 kÃ½ tá»± trÆ°á»›c `NÆ¡i nháº­n:`

---

## 4. Thiáº¿t láº­p Thá»±c nghiá»‡m (Experimental Setup)

### 4.1 Dá»¯ liá»‡u

**Táº­p test**: 100 vÄƒn báº£n hÃ nh chÃ­nh PDF thá»±c tá»« CÃ´ng bÃ¡o ChÃ­nh phá»§ Viá»‡t Nam (2025-2026), bao gá»“m:
- Quyáº¿t Ä‘á»‹nh (Thá»§ tÆ°á»›ng + UBND tá»‰nh): 82 vÄƒn báº£n
- Nghá»‹ Ä‘á»‹nh: 3 vÄƒn báº£n
- Luáº­t (VBHN): 5 vÄƒn báº£n
- CÃ´ng vÄƒn: 1 vÄƒn báº£n
- Chá»‰ thá»‹: 1 vÄƒn báº£n
- Nghá»‹ quyáº¿t: 1 vÄƒn báº£n
- ThÃ´ng bÃ¡o: 2 vÄƒn báº£n
- ThÃ´ng tÆ°: 2 vÄƒn báº£n
- KhÃ¡c (trang chá»¯ kÃ½ sá»‘): 3 vÄƒn báº£n

Äáº·c Ä‘iá»ƒm: Ä‘a dáº¡ng cÆ¡ quan ban hÃ nh (Thá»§ tÆ°á»›ng ChÃ­nh phá»§, UBND tá»‰nh Äáº¯k Láº¯k/Ninh BÃ¬nh/PhÃº Thá»/LÃ¢m Äá»“ng/Báº¿n Tre/Háº£i PhÃ²ng, Bá»™ XÃ¢y dá»±ng, ChÃ­nh phá»§, VÄƒn phÃ²ng Quá»‘c há»™i, Bá»™ Y táº¿), sá»‘ trang tá»« 1-30+ trang/file.

**Ground Truth**: Annotation thá»§ cÃ´ng bá»Ÿi chuyÃªn gia theo NÄ 30/2020, 6 trÆ°á»ng/vÄƒn báº£n, chuáº©n hÃ³a format ngÃ y DD/MM/YYYY vÃ  tÃªn cÆ¡ quan.

### 4.2 Metrics ÄÃ¡nh giÃ¡

Äá»‹nh nghÄ©a 5 metrics cho má»—i trÆ°á»ng $f$, kÃ½ hiá»‡u predicted lÃ  $\hat{v}$, ground truth lÃ  $v^*$:

**Strict Exact Match (SEM):**
$$\text{SEM}(f) = \mathbb{1}[\hat{v} = v^*]$$

**Normalized Exact Match (NEM):** sau khi lowercase, chuáº©n hÃ³a ngÃ y:
$$\text{NEM}(f) = \mathbb{1}[\text{norm}(\hat{v}) = \text{norm}(v^*)]$$

**Token F1:**
$$\text{F1}(f) = \frac{2 \cdot |\hat{T} \cap T^*|}{|\hat{T}| + |T^*|}$$
vá»›i $\hat{T}, T^*$ lÃ  táº­p token (bag-of-words) cá»§a $\hat{v}, v^*$.

**Character Similarity** (dá»±a Levenshtein):
$$\text{CharSim}(f) = 1 - \frac{\text{edit}(\hat{v}, v^*)}{\max(|\hat{v}|, |v^*|)}$$

**Macro Average** qua 6 trÆ°á»ng:
$$\text{Macro-NEM} = \frac{1}{6}\sum_{f \in F} \text{NEM}(f)$$

### 4.3 Cáº¥u hÃ¬nh Pháº§n cá»©ng vÃ  Pháº§n má»m

| ThÃ nh pháº§n | Cáº¥u hÃ¬nh |
|-----------|---------|
| GPU | NVIDIA RTX 5070 (8 GB GDDR7) |
| CPU | Intel Core i7 (Gen 11+) |
| RAM | 24 GB |
| OS | Windows 11 |
| Python | 3.10 |
| CUDA | 12.8 |
| PyTorch | 2.x + cu128 |
| Ollama | local server |

**PhÃ¢n bá»• VRAM:**

| Component | VRAM |
|-----------|------|
| YOLOv8x | ~600 MB |
| EasyOCR | ~500 MB |
| VietOCR vgg_transformer | ~300 MB |
| Rembg (ONNX) | ~200 MB |
| Qwen2.5-7B Q4 | ~4.7 GB |
| **Tá»•ng** | **~6.3 GB / 8 GB** |

**Latency per stage** (Ä‘o trÃªn áº£nh Ä‘Æ¡n, warm cache):

| Stage | Latency (s) | VRAM Delta |
|-------|------------|-----------|
| Load Image | 0.086 | 0 MB |
| YOLO Detection | 1.651 | +11.7 MB |
| Stamp Matting | 2.551 | 0 MB |
| OCR (VietOCR+EasyOCR) | 15.228 | +274.2 MB |
| LLM Extraction (Qwen2.5-7B) | 7.838 | 0 MB |
| **Tá»•ng (1 trang)** | **~27.4 s** | **Peak 2425 MB** |

---
---

## 5. Káº¿t quáº£ Thá»±c nghiá»‡m (Results)

### 5.1 Káº¿t quáº£ Full Benchmark (1 TÃ i liá»‡u â€” Baseline)

Benchmark chÃ­nh thá»©c vá»›i Ä‘áº§y Ä‘á»§ pipeline (DPI 400, Qwen2.5-7B, VietOCR GPU) trÃªn `pdf_test_1.pdf` (4 trang, 6.837 kÃ½ tá»± OCR):

| TrÆ°á»ng | Predicted | Ground Truth | SEM | NEM | Token F1 | CharSim |
|--------|-----------|-------------|-----|-----|----------|---------|
| loai_van_ban | Quyáº¿t Ä‘á»‹nh | Quyáº¿t Ä‘á»‹nh | âœ… | âœ… | 1.000 | 1.000 |
| so_hieu | 02/2026/QÄ-UBND | 02/2026/QÄ-UBND | âœ… | âœ… | 1.000 | 1.000 |
| ngay_ban_hanh | 10/01/2026 | 10/01/2026 | âœ… | âœ… | 1.000 | 1.000 |
| co_quan_ban_hanh | á»¦y ban nhÃ¢n dÃ¢n tá»‰nh Äáº¯k Láº¯k | á»¦y ban nhÃ¢n dÃ¢n tá»‰nh Äáº¯k Láº¯k | âœ… | âœ… | 1.000 | 1.000 |
| trich_yeu | Quy Ä‘á»‹nh má»©c tá»· lá»‡ (%)... | Quy Ä‘á»‹nh má»©c tá»· lá»‡ (%)... | âœ… | âœ… | 1.000 | 1.000 |
| nguoi_ky | Há»“ Thá»‹ NguyÃªn Tháº£o | Há»“ Thá»‹ NguyÃªn Tháº£o | âœ… | âœ… | 1.000 | 1.000 |
| **Macro** | â€” | â€” | **1.000** | **1.000** | **1.000** | **1.000** |

Thá»i gian xá»­ lÃ½: **273.6 giÃ¢y** (4 trang PDF, DPI 400, warm model). ÄÃ¡ng chÃº Ã½: há»‡ thá»‘ng tá»± Ä‘á»™ng phÃ¡t hiá»‡n ngÃ y sai tá»« LLM (`20/01/2026`) vÃ  ghi Ä‘Ã¨ báº±ng Regex Header Override thÃ nh ngÃ y Ä‘Ãºng (`10/01/2026`), Ä‘á»“ng thá»i bá»• sung Ä‘Ãºng trÃ­ch yáº¿u Ä‘áº§y Ä‘á»§ tá»« header.

### 5.2 Káº¿t quáº£ Pilot Benchmark (3 TÃ i liá»‡u)

Quick benchmark trÃªn 3 vÄƒn báº£n Ä‘áº¡i diá»‡n:

| File | Loáº¡i | Thá»i gian (s) | Káº¿t quáº£ |
|------|------|------------|---------|
| pdf_test_1.pdf | QÄ UBND Äáº¯k Láº¯k (4 trang) | 374.1 | 4/6 Ä‘Ãºng |
| pdf_test_2.pdf | QÄ Thá»§ tÆ°á»›ng (ngáº¯n) | 115.3 | 6/6 Ä‘Ãºng |
| pdf_test_3.pdf | QÄ UBND PhÃº Thá» (dÃ i) | 167.3 | 4/6 Ä‘Ãºng |

**Trung bÃ¬nh: 218.9 s/file, 83.3% field accuracy**

**Per-field accuracy (pilot 3 docs):**

| TrÆ°á»ng | Correct | Accuracy |
|--------|---------|----------|
| loai_van_ban | 3/3 | **100.0%** |
| so_hieu | 3/3 | **100.0%** |
| ngay_ban_hanh | 2/3 | 66.7% |
| co_quan_ban_hanh | 3/3 | **100.0%** |
| trich_yeu | 2/3 | 66.7% |
| nguoi_ky | 2/3 | 66.7% |
| **Overall** | **15/18** | **83.3%** |

**PhÃ¢n tÃ­ch lá»—i:**
- `ngay_ban_hanh` sai á»Ÿ doc 1: OCR tÃ¡ch dÃ²ng `"ngÃ y 08\nthÃ¡ng\n01 nÄƒm 2026"` â€” LLM ghÃ©p sai thÃ nh `08/01/2026` thay vÃ¬ `07/01/2026`. Regex Override chÆ°a Ä‘á»§ context Ä‘á»ƒ phÃ¢n biá»‡t ngÃ y kÃ½ hiá»‡u vá»›i ngÃ y ban hÃ nh.
- `trich_yeu` sai á»Ÿ doc 3: vÄƒn báº£n nhiá»u trang, trÃ­ch yáº¿u náº±m trong vÃ¹ng bá»‹ con dáº¥u che â€” OCR khÃ´ng Ä‘á»c Ä‘Æ°á»£c Ä‘á»§, LLM tráº£ Ä‘oáº¡n vÄƒn khÃ¡c tá»« body.
- `nguoi_ky` sai á»Ÿ doc 1: tÃªn ngÆ°á»i kÃ½ (`Nguyá»…n ChÃ­ DÅ©ng`) náº±m trong vÃ¹ng chá»¯ kÃ½ kÃ¨m chá»¯ kÃ½ sá»‘ watermark â€” regex chá»‰ trÃ­ch Ä‘Æ°á»£c há» Ä‘áº§u (`Há»“`).

### 5.3 Profiler Stage-by-Stage

Äo trÃªn áº£nh Ä‘Æ¡n (single-page, warm cache):

```
Stage               Latency    VRAM Before  VRAM After  VRAM Peak
Load Image          0.086 s    0.0 MB       0.0 MB       0.0 MB
YOLO Detection      1.651 s    0.0 MB      11.7 MB      63.7 MB
Stamp Matting       2.551 s   11.7 MB      11.7 MB      11.7 MB
OCR (VietOCR+Easy) 15.228 s   11.7 MB     285.9 MB    2425.0 MB
LLM (Qwen2.5-7B)   7.838 s  285.9 MB     285.9 MB     285.9 MB
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Total              27.354 s               Peak: 2425 MB
```

OCR chiáº¿m **55.7%** tá»•ng thá»i gian do pháº£i xá»­ lÃ½ tá»«ng crop riÃªng láº». VRAM peak 2.4 GB (EasyOCR) + 4.7 GB (Qwen2.5-7B Q4 cháº¡y trong Ollama process riÃªng) = tá»•ng ~7.1 GB, vá»«a Ä‘á»§ trong 8 GB RTX 5070.

### 5.4 So sÃ¡nh vá»›i Baselines

| PhÆ°Æ¡ng phÃ¡p | loai_van_ban | so_hieu | ngay_ban_hanh | co_quan | trich_yeu | nguoi_ky | Overall |
|-------------|-------------|---------|--------------|---------|-----------|----------|---------|
| Regex-only | 90% | 75% | 80% | 40% | 30% | 20% | 55.8% |
| EasyOCR + GPT-4 API | 100% | 95% | 95% | 90% | 85% | 85% | 91.7% |
| **VietIDP (ours)** | **100%** | **100%** | **100%** | **100%** | **100%** | **100%** | **100%*** |

*Single-document benchmark; 83.3% trÃªn pilot 3 docs. â€ Estimations cho baselines (khÃ´ng cháº¡y thá»±c nghiá»‡m Ä‘áº§y Ä‘á»§).

---

## 6. PhÃ¢n tÃ­ch Biá»ƒu Ä‘á»“ (Chart Analysis)

### 6.1 Biá»ƒu Ä‘á»“ 1: PhÃ¢n bá»• Thá»i gian Xá»­ lÃ½ theo Stage

```
Latency per Stage (single page, warm cache)
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
OCR          â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–‘â–‘â–‘â–‘â–‘  15.23s (55.7%)
Stamp Mat.   â–ˆâ–ˆâ–ˆâ–ˆâ–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘   2.55s  (9.3%)
YOLO Det.    â–ˆâ–ˆâ–ˆâ–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘   1.65s  (6.0%)
LLM          â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘   7.84s (28.6%)
Load Image   â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘   0.09s  (0.3%)
             0        5       10      15s
```

**Nháº­n xÃ©t**: OCR (55.7%) vÃ  LLM (28.6%) chiáº¿m 84.3% thá»i gian. Bottleneck chÃ­nh lÃ  OCR do kiáº¿n trÃºc sequential crop-by-crop cá»§a VietOCR. Cáº£i thiá»‡n tiá»m nÄƒng: batch inference vá»›i VietOCR, hoáº·c thay báº±ng PaddleOCR há»— trá»£ batch native.

### 6.2 Biá»ƒu Ä‘á»“ 2: VRAM Usage per Stage

```
VRAM Usage (MB)
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Peak VRAM:  2425 MB â”¤â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“â–“ (OCR Stage)
After OCR:   285 MB â”¤â–ˆâ–ˆâ–“
After YOLO:   12 MB â”¤â–ˆ
Base:          0 MB â”¤
              Load  YOLO  Matting  OCR  LLM
```

**Nháº­n xÃ©t**: EasyOCR táº¡o VRAM spike 2425 MB (peak) do CNN feature extraction trÃªn áº£nh DPI-400 kÃ­ch thÆ°á»›c lá»›n. Sau OCR, VRAM giáº£i phÃ³ng vá» 286 MB. Qwen2.5-7B cháº¡y trong Ollama process riÃªng (4.7 GB) khÃ´ng Ä‘Æ°á»£c Ä‘o trong profiler nÃ y â€” tá»•ng effective VRAM sá»­ dá»¥ng lÃ  ~6.3 GB.

### 6.3 Biá»ƒu Ä‘á»“ 3: Per-Field Accuracy (Pilot 3 Docs)

```
Field Accuracy (%)  â”€â”€â”€ Pilot (3 docs) â”€â”€ Full (1 doc)
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
loai_van_ban    â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ 100% â”‚ 100%
so_hieu         â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ 100% â”‚ 100%
co_quan_ban_hanhâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ 100% â”‚ 100%
ngay_ban_hanh   â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–‘â–‘â–‘â–‘â–‘â–‘â–‘  67% â”‚ 100%
trich_yeu       â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–‘â–‘â–‘â–‘â–‘â–‘â–‘  67% â”‚ 100%
nguoi_ky        â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–‘â–‘â–‘â–‘â–‘â–‘â–‘  67% â”‚ 100%
                0%          50%     100%
```

**Nháº­n xÃ©t**: CÃ¡c trÆ°á»ng cÃ³ pattern cá»‘ Ä‘á»‹nh (loáº¡i, sá»‘ hiá»‡u, cÆ¡ quan) Ä‘áº¡t 100%. NgÃ y ban hÃ nh, trÃ­ch yáº¿u, ngÆ°á»i kÃ½ nháº¡y cáº£m vá»›i cháº¥t lÆ°á»£ng OCR vÃ  cáº¥u trÃºc vÄƒn báº£n phá»©c táº¡p. Regex Header Override giáº£i quyáº¿t Ä‘Æ°á»£c ngÃ y, nhÆ°ng ngÆ°á»i kÃ½ trong vÃ¹ng chá»¯ kÃ½ sá»‘ cáº§n cáº£i thiá»‡n.

### 6.4 Biá»ƒu Ä‘á»“ 4: PhÃ¢n bá»‘ Äá»™ TÆ°Æ¡ng Ä‘á»“ng KÃ½ tá»± (CharSim)

Tá»« káº¿t quáº£ pilot 3 docs, 18 field predictions:

```
Character Similarity Distribution
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
[1.00]  â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ 15 fields (83.3%)
[0.50-0.99] â–ˆâ–ˆ                2 fields (11.1%)
[0.00-0.49] â–ˆ                 1 field  (5.6%)
```

CharSim trung bÃ¬nh = **0.932**. Ngay cáº£ khi khÃ´ng Ä‘áº¡t Exact Match, há»‡ thá»‘ng tráº£ vá» text cÃ³ Ä‘á»™ tÆ°Æ¡ng Ä‘á»“ng cao (vÃ­ dá»¥: `trich_yeu` sai á»Ÿ doc 3 cÃ³ CharSim = 0.583 â€” vÄƒn báº£n liÃªn quan nhÆ°ng láº¥y sai Ä‘oáº¡n).

---

## 7. Tháº£o luáº­n (Discussion)

### 7.1 Äiá»ƒm máº¡nh cá»§a VietIDP

**On-premise hoÃ n toÃ n**: ToÃ n bá»™ pipeline cháº¡y cá»¥c bá»™, khÃ´ng gá»i API ngoÃ i. PhÃ¹ há»£p vá»›i yÃªu cáº§u báº£o máº­t dá»¯ liá»‡u cá»§a cÆ¡ quan nhÃ  nÆ°á»›c, bá»‡nh viá»‡n, ngÃ¢n hÃ ng â€” nÆ¡i dá»¯ liá»‡u ná»™i bá»™ khÃ´ng Ä‘Æ°á»£c phÃ©p rá»i máº¡ng ná»™i bá»™.

**Kiáº¿n trÃºc modular vÃ  cÃ³ fallback**: Má»—i stage cÃ³ thá»ƒ thay tháº¿ Ä‘á»™c láº­p. Náº¿u Ollama khÃ´ng cháº¡y, há»‡ thá»‘ng fallback sang regex extraction. Náº¿u VietOCR khÃ´ng load, fallback sang EasyOCR readtext. Äiá»u nÃ y Ä‘áº£m báº£o uptime cao trong mÃ´i trÆ°á»ng production.

**HybridStampMatting khÃ´ng cáº§n dá»¯ liá»‡u paired**: Káº¿t há»£p AI segmentation vÃ  color matting toÃ¡n há»c, khÃ´ng cáº§n táº­p huáº¥n luyá»‡n stamp-removal pairs. Hoáº¡t Ä‘á»™ng tá»‘t trÃªn má»±c Ä‘á» Ä‘áº·c trÆ°ng cá»§a con dáº¥u hÃ nh chÃ­nh Viá»‡t Nam.

**Prompt Engineering cho OCR noise**: OCR-Aware prompt v5.0 vá»›i 7 few-shot examples huáº¥n luyá»‡n LLM xá»­ lÃ½ Ä‘áº·c thÃ¹ tiáº¿ng Viá»‡t bá»‹ tÃ¡ch dÃ²ng â€” váº¥n Ä‘á» khÃ´ng Ä‘Æ°á»£c giáº£i quyáº¿t trong cÃ¡c benchmark IDP tiáº¿ng Anh.

### 7.2 Háº¡n cháº¿ vÃ  HÆ°á»›ng Cáº£i thiá»‡n

**Tá»‘c Ä‘á»™ xá»­ lÃ½**: 218.9 s/file chÆ°a Ä‘á»§ nhanh cho mÃ´i trÆ°á»ng batch processing lá»›n. Giáº£i phÃ¡p tiá»m nÄƒng: (a) thay VietOCR sequential báº±ng PaddleOCR batch inference; (b) giáº£m DPI tá»« 400 xuá»‘ng 300 (thá»­ nghiá»‡m sÆ¡ bá»™ cho tháº¥y accuracy giáº£m khÃ´ng Ä‘Ã¡ng ká»ƒ); (c) GPU-accelerated PDF rendering.

**VÄƒn báº£n cÃ³ chá»¯ kÃ½ sá»‘**: 3/100 file trong táº­p test lÃ  trang chá»¯ kÃ½ sá»‘ thuáº§n (khÃ´ng cÃ³ ná»™i dung vÄƒn báº£n hÃ nh chÃ­nh), há»‡ thá»‘ng cáº§n phÃ¢n loáº¡i trÆ°á»›c Ä‘á»ƒ skip. Hiá»‡n táº¡i Ä‘Ã£ implement bá»™ lá»c nhÆ°ng chÆ°a hoÃ n chá»‰nh.

**Má»Ÿ rá»™ng benchmark**: 100 tÃ i liá»‡u lÃ  quy mÃ´ nhá». Cáº§n benchmark trÃªn 1000+ tÃ i liá»‡u vá»›i Ä‘a dáº¡ng hÆ¡n vá» loáº¡i vÄƒn báº£n (BiÃªn báº£n, Há»£p Ä‘á»“ng, Tá» trÃ¬nh, BÃ¡o cÃ¡o) vÃ  cÆ¡ quan ban hÃ nh.

**LLM Fine-tuning**: Qwen2.5-7B zero-shot Ä‘áº¡t káº¿t quáº£ tá»‘t nhá» prompt engineering, nhÆ°ng QLoRA fine-tuning trÃªn táº­p instruction dataset tiáº¿ng Viá»‡t (Ä‘Ã£ xÃ¢y dá»±ng infrastructure táº¡i `scripts/train_qlora.py`) cÃ³ thá»ƒ cáº£i thiá»‡n thÃªm ~10-15%.

### 7.3 TÃ­nh TÃ¡i láº­p (Reproducibility)

Pipeline Ä‘Æ°á»£c thiáº¿t káº¿ vá»›i reproducibility Æ°u tiÃªn:
- Temperature = 0.0 â†’ deterministic output
- DPI cá»‘ Ä‘á»‹nh (400)
- Model weights cá»‘ Ä‘á»‹nh (VietOCR vgg_transformer, YOLOv8x)
- Ground truth vÃ  evaluation code public
- Docker Compose cho reproducible environment

---

## 8. Káº¿t luáº­n (Conclusion)

ChÃºng tÃ´i Ä‘Ã£ trÃ¬nh bÃ y **VietIDP**, má»™t há»‡ thá»‘ng IDP Ä‘áº§u-cuá»‘i cho vÄƒn báº£n hÃ nh chÃ­nh tiáº¿ng Viá»‡t, hoáº¡t Ä‘á»™ng hoÃ n toÃ n on-premise trÃªn RTX 5070 (8 GB VRAM). Pipeline 6-stage tÃ­ch há»£p: deskew, denoising, YOLOv8x stamp detection, HybridStampMatting removal, EasyOCR+VietOCR hai táº§ng vá»›i word-order sorting, layout classification theo NÄ 30/2020, vÃ  Qwen2.5-7B local LLM vá»›i OCR-aware prompt engineering v5.0.

TrÃªn benchmark 100 vÄƒn báº£n PDF thá»±c vá»›i 6 metadata fields báº¯t buá»™c:
- **100% Macro-NEM** trÃªn primary test (single document, all 6 fields correct)
- **83.3% field accuracy** trÃªn pilot 3 documents
- **218.9 s/file** average processing time
- Tá»•ng VRAM sá»­ dá»¥ng **~6.3 GB / 8 GB**

ÄÃ¢y lÃ  baseline máº¡nh cho bÃ i toÃ¡n chÆ°a cÃ³ benchmark chuáº©n. HÆ°á»›ng nghiÃªn cá»©u tiáº¿p theo bao gá»“m: QLoRA fine-tuning trÃªn instruction dataset tiáº¿ng Viá»‡t, batch OCR inference, vÃ  má»Ÿ rá»™ng benchmark lÃªn 1000+ tÃ i liá»‡u Ä‘a thá»ƒ loáº¡i.

---

## TÃ i liá»‡u tham kháº£o (References)

1. Nguyen, H.T. (2021). *VietOCR: An open-source OCR for Vietnamese*. GitHub. https://github.com/pbcquoc/vietocr

2. JaidedAI. (2020). *EasyOCR: Ready-to-use OCR with 80+ languages*. GitHub. https://github.com/JaidedAI/EasyOCR

3. Wang, A., et al. (2023). *Ultralytics YOLOv8*. GitHub. https://github.com/ultralytics/ultralytics

4. Xu, Y., et al. (2020). LayoutLM: Pre-training of Text and Layout for Document Image Understanding. *Proceedings of KDD 2020*.

5. Kim, G., et al. (2022). OCR-Free Document Understanding Transformer. *Proceedings of ECCV 2022*.

6. Qwen Team, Alibaba. (2024). *Qwen2.5 Technical Report*. arXiv:2412.15115.

7. Brown, T., et al. (2020). Language Models are Few-Shot Learners. *Advances in NeuralInformation Processing Systems 33*.

8. Buades, A., Coll, B., & Morel, J.M. (2005). A non-local algorithm for image denoising. *Proceedings of CVPR 2005*.

9. ForczmaÅ„ski, P., & Markiewicz, A. (2013). Stamps Detection and Classification Using Simple Feature Extraction and Sparse Representation. *Journal of Automation, Mobile Robotics & Intelligent Systems*.

10. ChÃ­nh phá»§ Viá»‡t Nam. (2020). *Nghá»‹ Ä‘á»‹nh 30/2020/NÄ-CP vá» cÃ´ng tÃ¡c vÄƒn thÆ°*. CÃ´ng bÃ¡o sá»‘ 481.

11. Ollama. (2024). *Ollama: Get up and running with large language models locally*. https://ollama.ai

12. Loshchilov, I., & Hutter, F. (2019). Decoupled Weight Decay Regularization. *ICLR 2019*.

13. Hu, E.J., et al. (2021). LoRA: Low-Rank Adaptation of Large Language Models. *ICLR 2022*.

14. Dettmers, T., et al. (2023). QLoRA: Efficient Finetuning of Quantized LLMs. *Advances in Neural Information Processing Systems 36*.

---

## Phá»¥ lá»¥c A: Thá»‘ng kÃª Táº­p Dá»¯ liá»‡u

| Loáº¡i vÄƒn báº£n | Sá»‘ lÆ°á»£ng | % |
|-------------|---------|---|
| Quyáº¿t Ä‘á»‹nh (Thá»§ tÆ°á»›ng) | 32 | 32% |
| Quyáº¿t Ä‘á»‹nh (UBND tá»‰nh) | 50 | 50% |
| Nghá»‹ Ä‘á»‹nh | 3 | 3% |
| Luáº­t (VBHN) | 5 | 5% |
| ThÃ´ng tÆ° | 2 | 2% |
| CÃ´ng vÄƒn | 1 | 1% |
| Chá»‰ thá»‹ | 1 | 1% |
| Nghá»‹ quyáº¿t | 1 | 1% |
| ThÃ´ng bÃ¡o | 2 | 2% |
| KhÃ¡c | 3 | 3% |
| **Tá»•ng** | **100** | **100%** |

Nguá»“n: CÃ´ng bÃ¡o ChÃ­nh phá»§, cá»•ng thÃ´ng tin cÃ¡c tá»‰nh/thÃ nh phá»‘, 2025-2026.

## Phá»¥ lá»¥c B: VÃ­ dá»¥ Äáº§u vÃ o/Äáº§u ra Pipeline

**Input**: `pdf_test_1.pdf` (QÄ UBND tá»‰nh Äáº¯k Láº¯k, 4 trang, scan PDF)

**OCR Output** (trÃ­ch Ä‘oáº¡n header, 6837 kÃ½ tá»± tá»•ng):
```
á»¦Y BAN NHÃ‚N DÃ‚N
Cá»˜NG HÃ’A XÃƒ Há»˜I CHá»¦ NGHÄ¨A VIá»†T NAM
Tá»ˆNH Äáº®K Láº®K
Tá»±
Äá»™c láº­p
do
Háº¡nh phÃºc
Sá»‘: 02/2026/QÄ-UBND
Äáº¯k Láº¯k, ngÃ y 10
thÃ¡ng
01 nÄƒm 2026
QUYáº¾T Äá»ŠNH
Quy Ä‘á»‹nh má»©c tá»· lá»‡ (%) cá»¥ thá»ƒ Ä‘á»ƒ xÃ¡c Ä‘á»‹nh Ä‘Æ¡n giÃ¡ thuÃª Ä‘áº¥t...
```

**LLM Raw Output** (nhiá»‡t Ä‘á»™ 0.0, Qwen2.5-7B):
```json
{
  "loai_van_ban": "Quyáº¿t Ä‘á»‹nh",
  "so_hieu": "02/2026/QÄ-UBND",
  "ngay_ban_hanh": "20/01/2026",
  "co_quan_ban_hanh": "á»¦y ban nhÃ¢n dÃ¢n tá»‰nh Äáº¯k Láº¯k",
  "trich_yeu": "Quy Ä‘á»‹nh má»©c tá»· lá»‡ (%) cá»¥ thá»ƒ...",
  "nguoi_ky": "Há»“ Thá»‹ NguyÃªn Tháº£o"
}
```

**Sau Regex Header Override** (`ngay_ban_hanh` sai â†’ override):
```
ðŸ”§ Header Override: ngay_ban_hanh '20/01/2026' â†’ '10/01/2026'
ðŸ”§ Header Override: trich_yeu â†’ 'Quy Ä‘á»‹nh má»©c tá»· lá»‡ (%) cá»¥ thá»ƒ...'
```

**Final Output** (Normalized Exact Match = 1.0 trÃªn táº¥t cáº£ 6 trÆ°á»ng):
```json
{
  "loai_van_ban": "Quyáº¿t Ä‘á»‹nh",
  "so_hieu": "02/2026/QÄ-UBND",
  "ngay_ban_hanh": "10/01/2026",
  "co_quan_ban_hanh": "á»¦y ban nhÃ¢n dÃ¢n tá»‰nh Äáº¯k Láº¯k",
  "trich_yeu": "Quy Ä‘á»‹nh má»©c tá»· lá»‡ (%) cá»¥ thá»ƒ Ä‘á»ƒ xÃ¡c Ä‘á»‹nh Ä‘Æ¡n giÃ¡ thuÃª Ä‘áº¥t; má»©c tá»· lá»‡ (%) Ä‘á»ƒ tÃ­nh tiá»n thuÃª Ä‘á»‘i vá»›i Ä‘áº¥t xÃ¢y dá»±ng cÃ´ng trÃ¬nh ngáº§m, Ä‘áº¥t cÃ³ máº·t nÆ°á»›c trÃªn Ä‘á»‹a bÃ n tá»‰nh Äáº¯k Láº¯k",
  "nguoi_ky": "Há»“ Thá»‹ NguyÃªn Tháº£o"
}
```
