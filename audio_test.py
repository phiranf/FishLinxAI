
import pyaudio
mic = pyaudio.PyAudio()
stream = mic.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, output=True, frames_per_buffer=2048)
stream.start_stream()

if __name__ == '__main__':
    while True:
        data = stream.read(1024)
        # Do something with sound

