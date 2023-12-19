
from pydub import AudioSegment
import os

def make_empty_mp3(output_file: str, seconds: float):
    num_segments = int(seconds * 1000)
    silence = AudioSegment.silent(duration=num_segments, frame_rate=24000)
    silence.export(output_file, format="mp3")


def trim_mp3(input_file: str, output_file: str, window_size: int = 50, window_interval: int = 20, silence_thr: float = -50):
    '''
    Silence detection with sliding window
    '''

    audio = AudioSegment.from_mp3(input_file)

    start_trim = 0
    end_trim = 0

    # Detect silence at the beginning
    while audio[start_trim:start_trim+window_size].dBFS < silence_thr:
        start_trim += window_interval

    # Detect silence at the end
    while audio[-end_trim-window_size:].dBFS < silence_thr:
        end_trim += window_interval

    trimmed_audio = audio[start_trim:-end_trim]
    trimmed_audio.export(output_file, format="mp3")

