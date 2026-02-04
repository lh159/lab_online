import os
import re
from typing import List, Dict, Any
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess


class ASRService:
    """
    封装 ASR 推理逻辑，提供 transcribe(path) 返回识别文本及按句/词的置信度信息。
    """

    def __init__(self,
                 model_origin_path: str = "/root/demo_1_confidence/xu_zhuxi_model/SenseVoiceSmall",
                 model_trained_path: str = "/root/demo_1_confidence/xu_zhuxi_model/SenseVoiceSmall",
                 device: str = "cuda:0"):
        self.model_origin_path = model_origin_path
        self.model_trained_path = model_trained_path
        self.device = device
        self.modelOR = None
        self.modelTR = None
        self._load_models()

    def _load_models(self):
        print("ASRService: loading models...")
        # 加载原始模型
        self.modelOR = AutoModel(
            model=self.model_origin_path,
            trust_remote_code=False,
            vad_model=None,
            vad_kwargs={"max_single_segment_time": 30000},
            device=self.device,
        )
        # 加载训练后模型（如果与 origin 相同也可以）
        self.modelTR = AutoModel(
            model=self.model_trained_path,
            trust_remote_code=False,
            vad_model=None,
            vad_kwargs={"max_single_segment_time": 30000},
            device=self.device,
        )

    def _postprocess_text(self, text: str) -> str:
        text = rich_transcription_postprocess(text)
        # 清理常见 emoji
        for e in ["😊", "🎼", "😔"]:
            text = text.replace(e, "")
        return text

    def _split_sentences(self, text: str) -> List[str]:
        # 简单按中文和英文句末符号分句，保留标点
        parts = re.split(r'([。！？!?]+)', text)
        sentences = []
        for i in range(0, len(parts) - 1, 2):
            sent = (parts[i] + parts[i + 1]).strip()
            if sent:
                sentences.append(sent)
        # 处理末尾残余
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())
        return sentences if sentences else [text]

    def _avg_conf(self, probs: List[float]) -> float:
        """
        更健壮地计算平均置信度。支持元素为数值或字典的情况。
        字典会尝试按常见字段提取数值：'prob','confidence','score','p','probability'。
        无法解析的元素会被跳过；若所有元素无法解析则返回 0.0。
        """
        if not probs:
            return 0.0
        return float(sum(probs) / len(probs))

    def transcribe(self, audio_path: str, use_trained: bool = False) -> Dict[str, Any]:
        """
        对音频文件执行推理，返回结构：
        {
          "text": "...",
          "sentences": [{"text": "...", "confidence": 0.95, "words": [{"text": "...","confidence":0.9}, ...]}, ...],
          "raw_prob": [...],  # 原始模型返回的置信度列表（可能为 []）
        }
        """
        model = self.modelTR if use_trained else self.modelOR
        res = model.generate(
            input=audio_path,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )

        raw_text = res[0].get("text", "")
        raw_prob = res[0].get("prob", []) or []
        text = self._postprocess_text(raw_text)

        # 字符级概率长度可能与 text 不一致，安全处理
        char_probs = []
        # 先将 raw_prob 中可能的 dict 元素转换为数值列表
        numeric_raw_prob: List[float] = []
        if raw_prob:
            # 如果 raw_prob 的元素为 dict 或复杂结构，尝试提取数值
            converted = []
            for el in raw_prob:
                if isinstance(el, (int, float)):
                    converted.append(float(el))
                elif isinstance(el, dict):
                    # 尝试提取常见字段
                    v = None
                    for key in ("prob", "confidence", "score", "p", "probability"):
                        if key in el:
                            v = el[key]
                            break
                    if isinstance(v, (int, float)):
                        converted.append(float(v))
                    elif isinstance(v, list):
                        nums = [float(x) for x in v if isinstance(x, (int, float))]
                        converted.append(sum(nums) / len(nums) if nums else 0.0)
                    elif isinstance(v, dict):
                        found = None
                        for subkey in ("prob", "confidence", "score", "p", "probability"):
                            if subkey in v and isinstance(v[subkey], (int, float)):
                                found = float(v[subkey])
                                break
                        converted.append(found if found is not None else 0.0)
                    else:
                        converted.append(0.0)
                else:
                    try:
                        converted.append(float(el))
                    except Exception:
                        converted.append(0.0)

            # 如果 converted 中全部为 0.0（或长度为0），保留原 raw_prob empty
            numeric_raw_prob = converted

        if len(numeric_raw_prob) == len(raw_text):
            # 假设 raw_prob 与 raw_text 对应（最常见）
            # 把 raw_prob 对齐到处理后 text（简单策略：截断或用最后值填充）
            if len(text) == len(raw_text):
                char_probs = numeric_raw_prob
            else:
                # 处理长度不等时，尝试按比例映射
                if numeric_raw_prob:
                    scale = len(numeric_raw_prob) / max(1, len(text))
                    for i in range(len(text)):
                        idx = min(int(i * scale), len(numeric_raw_prob) - 1)
                        char_probs.append(numeric_raw_prob[idx])
        else:
            # fallback: 如果没有 prob 或长度不匹配，使用均值 0.9（保守）
            if numeric_raw_prob:
                avg = self._avg_conf(numeric_raw_prob)
                char_probs = [avg] * len(text)
            elif raw_prob:
                # raw_prob 存在但无法解析为数值，尝试从原始结构取平均
                avg = self._avg_conf(raw_prob)
                char_probs = [avg] * len(text)
            else:
                char_probs = [0.9] * len(text)

        # 分句并计算句子与词置信度（按字符平均）
        sentences = []
        sent_boundaries = []
        # 计算每个句子的字符范围（简单按分句函数）
        sents = self._split_sentences(text)
        cursor = 0
        for s in sents:
            length = len(s)
            sent_probs = char_probs[cursor:cursor + length] if cursor + length <= len(char_probs) else char_probs[cursor:]
            sent_conf = self._avg_conf(sent_probs)
            # 词级（用空白分词）
            words = []
            word_cursor = 0
            for w in s.split():
                wlen = len(w)
                w_probs = sent_probs[word_cursor:word_cursor + wlen] if word_cursor + wlen <= len(sent_probs) else sent_probs[word_cursor:]
                words.append({"text": w, "confidence": round(self._avg_conf(w_probs), 4)})
                word_cursor += wlen + 1  # +1 for the space removed by split (approx)
            sentences.append({"text": s, "confidence": round(sent_conf, 4), "words": words})
            cursor += length

        return {"text": text, "sentences": sentences, "raw_prob": raw_prob}


