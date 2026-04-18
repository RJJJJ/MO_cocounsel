# Day 65 Acceptance - Case Metadata Generation Layer v1

## 本輪功能對應
對應功能總表：
- A. CoCounsel 核心能力清單
  - 法律研究 Research
    - 案例導向研究摘要
    - 法條導向研究摘要
    - query-to-issue matching

本輪只補「模型生成層」，不改 Day 64 attach/demo 主體：
1. 批跑 prompt 模板（6 欄）
2. 批量 metadata generation script
3. short/medium/long 分流策略
4. generation acceptance 文件

## 新增 / 調整檔案
- `prompts/case_metadata_v1_system.txt`
- `prompts/case_metadata_v1_user.txt`
- `crawler/prep/generate_case_metadata_v1.py`
- `crawler/prep/build_case_metadata_v1.py`（小改：支援 sentence_id 優先索引）
- `docs/day65_case_metadata_generation_acceptance.md`

## 模型設定（可覆寫）
### 預設主模型（全量主跑）
- model_name: `Qwen/Qwen3-8B-Instruct`
- mode: instruct（non-thinking）
- quantization: `awq-4bit`（可切 `gptq-4bit`）
- backend: `transformers`（可改，程式保持可配置）

### 預設備用模型（補洞/複核）
- model_name: `google/gemma-3-12b-it`
- 用途：缺欄、JSON 不合法、或指定 long case 補跑
- 非全量主跑

### 預設 generation config
- `temperature=0.1`
- `top_p=0.85`
- `max_new_tokens=260`
- `repetition_penalty=1.05`
- `do_sample=false`
- JSON-only output
- 單案單輪；失敗才重試

## Prompt 策略（批跑版）
- 任務定義為「資訊抽取 + 保守歸納」
- 繁體中文
- 固定 6 欄 JSON schema
- 禁止 null（字串用 `""`、陣列用 `[]`）
- 明確欄位長度與來源偏好：
  - `case_summary`：80-140 字
  - `holding`：40-100 字
  - `disputed_issues`：2-5 項
  - `legal_basis`：2-8 項
  - `reasoning_summary`：100-180 字
  - `doctrinal_point`：50-120 字

## 長短案分流（可調閾值）
- `short`（`<= short_char_threshold`, 預設 3800）
  - 直接送全文生成 6 欄
- `medium`（`short < chars <= medium_char_threshold`, 預設 14000）
  - 取前段（事實/背景）+ 理由段（heading block）+ 尾段（結論）
- `long`（`> medium_char_threshold`）
  - 不送全文
  - 先抽關鍵片段：前段 + 爭點/理由/結論 heading block + 關鍵句 + 尾段
  - 片段不足允許留空，不硬補

## 本地執行方式
### 1) 主跑（Qwen3-8B）
```bash
python crawler/prep/generate_case_metadata_v1.py \
  --backend transformers \
  --model-name Qwen/Qwen3-8B-Instruct \
  --quantization awq-4bit \
  --temperature 0.1 \
  --top-p 0.85 \
  --max-new-tokens 260 \
  --repetition-penalty 1.05 \
  --start 0 --end 0 --limit 0
```

### 2) 續跑
```bash
python crawler/prep/generate_case_metadata_v1.py --resume
```

### 3) 啟用 Gemma 3 12B 補跑
```bash
python crawler/prep/generate_case_metadata_v1.py \
  --fallback-enabled \
  --fallback-model-name google/gemma-3-12b-it \
  --fallback-backend transformers \
  --fallback-quantization awq-4bit \
  --fallback-on-long
```

### 4) 餵給 Day64 builder + attach（既有流程）
```bash
python crawler/prep/build_case_metadata_v1.py \
  --model-metadata data/eval/model_generated_metadata_output.jsonl
python crawler/prep/attach_case_metadata_v1.py
```

## 生成輸出路徑
- 預設：`data/eval/model_generated_metadata_output.jsonl`

## 生成 JSONL 格式
每列包含：
- `sentence_id`
- `authoritative_case_number`
- `core_case_metadata`
- `generated_digest_metadata`（6 欄）
- `case_metadata_v1`（同 6 欄）
- `generation_meta`（route/model/backend/json_valid/fallback_applied 等）

6 欄固定 shape：
```json
{
  "case_summary": "...",
  "holding": "...",
  "disputed_issues": ["...", "..."],
  "legal_basis": ["...", "..."],
  "reasoning_summary": "...",
  "doctrinal_point": "..."
}
```

## build_case_metadata_v1.py 小改說明
- 原先主要以 `authoritative_case_number` 對齊 model/baseline metadata。
- 本輪新增 `sentence_id` 優先索引，並保留 case_number fallback。
- 不改 deterministic fallback 規則，不改 attach 流程。

## Known limitations
1. `transformers` backend 需本地已有相容權重與套件；本檔不內建下載流程。
2. 4-bit（AWQ/GPTQ）實際載入方式依本地模型包裝而異；腳本保持可配置但不綁死單一 provider。
3. 長案片段抽取為啟發式，仍可能漏掉少量深層理由段。
4. 本輪不做 reranker、BM25+ 改造、agent/planner 或多輪自我反思。
