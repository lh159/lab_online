import os
import re
import time
from typing import List, Dict, Any, Optional
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess


class ASRService:
    """
    封装 ASR 推理逻辑，支持两个模型：
    - base_model: 基础模型，未经个性化微调
    - personal_model: 个人专属模型（xu_zhuxi_model）
    
    提供 transcribe() 返回识别文本及按句/词的置信度信息。
    """

    def __init__(self,
                 base_model_path: str = "/root/demo_1_confidence/base_model/SenseVoiceSmall",
                 personal_model_path: str = "/root/demo_1_confidence/xu_zhuxi_model/SenseVoiceSmall",
                 device: str = "cuda:0"):
        self.base_model_path = base_model_path
        self.personal_model_path = personal_model_path
        self.device = device
        self.model_base = None
        self.model_personal = None
        self._load_models()

    def _load_models(self):
        print("ASRService: loading models...")
        load_start = time.time()
        
        # 加载基础模型
        print(f"  Loading base model from: {self.base_model_path}")
        self.model_base = AutoModel(
            model=self.base_model_path,
            trust_remote_code=False,
            vad_model=None,
            vad_kwargs={"max_single_segment_time": 30000},
            device=self.device,
        )
        print(f"  Base model loaded in {time.time() - load_start:.2f}s")
        
        # 加载个人专属模型
        personal_load_start = time.time()
        print(f"  Loading personal model from: {self.personal_model_path}")
        self.model_personal = AutoModel(
            model=self.personal_model_path,
            trust_remote_code=False,
            vad_model=None,
            vad_kwargs={"max_single_segment_time": 30000},
            device=self.device,
        )
        print(f"  Personal model loaded in {time.time() - personal_load_start:.2f}s")
        print("ASRService: all models loaded successfully!")

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

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（基于编辑距离）
        返回 0-1 之间的相似度分数
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        
        # 简单的字符级相似度计算
        set1 = set(text1)
        set2 = set(text2)
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0

    def _calculate_wer(self, reference: str, hypothesis: str) -> float:
        """
        计算 Word Error Rate (WER)
        简化版本：基于空格分词
        """
        ref_words = reference.split()
        hyp_words = hypothesis.split()
        
        if not ref_words:
            return 0.0 if not hyp_words else 1.0
        
        # 简单的编辑距离计算
        m, n = len(ref_words), len(hyp_words)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
            
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_words[i-1] == hyp_words[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        return dp[m][n] / m if m > 0 else 0.0

    def transcribe(self, audio_path: str, model_type: str = "base") -> Dict[str, Any]:
        """
        对音频文件执行推理，返回结构：
        {
          "text": "...",
          "sentences": [{"text": "...", "confidence": 0.95, "words": [{"text": "...","confidence":0.9}, ...]}, ...],
          "raw_prob": [...],
          "model_type": "base" | "personal",
          "processing_time_ms": 123.45
        }
        
        Args:
            audio_path: 音频文件路径
            model_type: "base" 或 "personal"
        """
        model = self.model_base if model_type == "base" else self.model_personal
        model_name = "base_model" if model_type == "base" else "xu_zhuxi_model"
        
        start_time = time.time()
        
        res = model.generate(
            input=audio_path,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )
        
        processing_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
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

        return {
            "text": text, 
            "sentences": sentences, 
            "raw_prob": raw_prob,
            "model_type": model_type,
            "model_name": model_name,
            "processing_time_ms": round(processing_time, 2)
        }

    def compare_models(self, audio_path: str) -> Dict[str, Any]:
        """
        同时调用两个模型进行对比
        返回两个模型的识别结果和统计分析
        """
        # 并行调用两个模型
        import asyncio
        
        async def run_comparison():
            loop = asyncio.get_running_loop()
            
            # 在线程池中并行执行两个模型的推理
            base_result, personal_result = await asyncio.gather(
                loop.run_in_executor(None, lambda: self.transcribe(audio_path, "base")),
                loop.run_in_executor(None, lambda: self.transcribe(audio_path, "personal")),
            )
            
            return base_result, personal_result
        
        # 如果在同步环境中执行
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            base_result, personal_result = executor.submit(
                lambda: (self.transcribe(audio_path, "base"), 
                         self.transcribe(audio_path, "personal"))
            ).result()
        
        # 计算统计分析
        text1 = base_result.get("text", "")
        text2 = personal_result.get("text", "")
        
        # 计算整体置信度
        base_conf = base_result.get("sentences", [])
        personal_conf = personal_result.get("sentences", [])
        
        avg_base_conf = sum(s.get("confidence", 0) for s in base_conf) / len(base_conf) if base_conf else 0
        avg_personal_conf = sum(s.get("confidence", 0) for s in personal_conf) / len(personal_conf) if personal_conf else 0
        
        # 计算相似度和 WER
        similarity = self._calculate_similarity(text1, text2)
        wer = self._calculate_wer(text1, text2)
        
        # 统计差异
        same_chars = sum(1 for c1, c2 in zip(text1, text2) if c1 == c2)
        diff_chars = abs(len(text1) - len(text2)) + sum(1 for c1, c2 in zip(text1[:min(len(text1), len(text2))], text2[:min(len(text1), len(text2))]) if c1 != c2)
        
        return {
            "base_model": base_result,
            "personal_model": personal_result,
            "statistics": {
                "similarity": round(similarity * 100, 2),  # 百分比
                "wer": round(wer * 100, 2),  # Word Error Rate 百分比
                "avg_confidence_base": round(avg_base_conf * 100, 2),
                "avg_confidence_personal": round(avg_personal_conf * 100, 2),
                "char_count_base": len(text1),
                "char_count_personal": len(text2),
                "same_chars": same_chars,
                "diff_chars": diff_chars,
                "total_chars": max(len(text1), len(text2)),
            },
            "comparison_timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }
