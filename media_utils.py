import cv2
import pyaudio
import threading

# Audio Config
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

class AudioRecorder:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording = False

    def start(self):
        self.recording = True
        self.stream = self.audio.open(format=FORMAT, channels=CHANNELS,
                                      rate=RATE, input=True,
                                      frames_per_buffer=CHUNK)

    def get_chunk(self):
        if self.recording and self.stream:
            try:
                return self.stream.read(CHUNK, exception_on_overflow=False)
            except:
                return None
        return None

    def stop(self):
        self.recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

class AudioPlayer:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=FORMAT, channels=CHANNELS,
                                      rate=RATE, output=True,
                                      frames_per_buffer=CHUNK)

    def play(self, data):
        try:
            self.stream.write(data)
        except:
            pass
            
    def cleanup(self):
        self.stream.stop_stream()
        self.stream.close()

class VideoCamera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0) # Open default camera
        
    def get_frame_bytes(self):
        ret, frame = self.cap.read()
        if ret:
            # Downscale for network performance
            frame = cv2.resize(frame, (320, 240))
            # Compress to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            return buffer.tobytes()
        return None

    def cleanup(self):
        self.cap.release()