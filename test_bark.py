

import scipy
from transformers import AutoProcessor, BarkModel
import torch

processor = AutoProcessor.from_pretrained("suno/bark")
model = BarkModel.from_pretrained("suno/bark").cuda()

voice_preset = "v2/zh_speaker_0"
# bark 中文奇怪口音无法解决
# 英文可以
text = "第一节:听后记录信息:听两遍短文，根据所听内容和提示，将所缺的关键信息填写在相应位置上，每空只需填写一个词。"

def generate_audio(text, voice_preset, output_file='bark_out.wav'):
    # inputs = processor(text, voice_preset=voice_preset)
    
    inputs = processor(
        text=[text],
        return_tensors="pt",
    )
    inputs = inputs.to("cuda")

    audio_array = model.generate(**inputs)
    audio_array = audio_array.cpu().numpy().squeeze()

    sample_rate = model.generation_config.sample_rate
    print('sample rate', sample_rate)
    scipy.io.wavfile.write(output_file, rate=sample_rate, data=audio_array)

generate_audio(text, voice_preset)

