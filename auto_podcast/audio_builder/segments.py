


class WhiteSpace():

    def __init__(self, time: float):
        self.time = time
    
    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f'WhiteSpace(time={self.time})'

class TextSegment():
    
    def __init__(self, text: str, voice: str, rate: float=1.0, volume: float=1.0):
        self.text = text
        self.voice = voice
        self.rate = rate
        self.volume = volume
    
    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f'TextSegment({repr(self.text)}, {repr(self.voice)}, rate={self.rate}, volume={self.volume})'


