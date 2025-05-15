import asyncio
from config.logger import setup_logging
import os
import re
from abc import ABC, abstractmethod
from core.utils.tts import MarkdownCleaner
from core.utils.util import audio_to_data

TAG = __name__
logger = setup_logging()


class TTSProviderBase(ABC):
    def __init__(self, config, delete_audio_file):
        self.delete_audio_file = delete_audio_file
        self.output_file = config.get("output_dir")

    @abstractmethod
    def generate_filename(self):
        pass

    def to_tts(self, text):
        tmp_file = self.generate_filename()
        try:
            max_repeat_time = 5
            text = MarkdownCleaner.clean_markdown(text)
            # 正则匹配 <emo> 和 </emo> 之间的内容
            emo_pattern = r"<emo>([a-zA-Z]+)</emo>"
            # 正则匹配 <face> 和 </face> 之间的内容
            face_pattern = r"<face>([a-zA-Z]+)</face>"
            # 正则匹配 <act> 和 </act> 之间的内容
            act_pattern = r"<act>([a-zA-Z]+)</act>"
            # 提取 emo、face 和 act 内容
            emo_match = re.search(emo_pattern, text)
            face_match = re.search(face_pattern, text)
            act_match = re.search(act_pattern, text)
            # 去除整个 <emo>...</emo>、<face>...</face> 和 <act>...</act> 部分
            if emo_match:
                self.emo_content = emo_match.group(1)
                text = re.sub(emo_pattern, '', text)
            if face_match:
                self.face_content = face_match.group(1)
                text = re.sub(face_pattern, '', text)
            if act_match:
                self.act_content = act_match.group(1)
                text = re.sub(act_pattern, '', text)
            while not os.path.exists(tmp_file) and max_repeat_time > 0:
                try:
                    asyncio.run(self.text_to_speak(text, tmp_file))
                except Exception as e:
                    logger.bind(tag=TAG).warning(
                        f"语音生成失败{5 - max_repeat_time + 1}次: {text}，错误: {e}"
                    )
                    # 未执行成功，删除文件
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
                    max_repeat_time -= 1

            if max_repeat_time > 0:
                logger.bind(tag=TAG).info(
                    f"语音生成成功: {text}:{tmp_file}，重试{5 - max_repeat_time}次"
                )
            else:
                logger.bind(tag=TAG).error(
                    f"语音生成失败: {text}，请检查网络或服务是否正常"
                )

            return tmp_file
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to generate TTS file: {e}")
            return None

    @abstractmethod
    async def text_to_speak(self, text, output_file):
        pass

    def audio_to_pcm_data(self, audio_file_path):
        """音频文件转换为PCM编码"""
        return audio_to_data(audio_file_path, is_opus=False)

    def audio_to_opus_data(self, audio_file_path):
        """音频文件转换为Opus编码"""
        return audio_to_data(audio_file_path, is_opus=True)
