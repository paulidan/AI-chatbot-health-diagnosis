import pyaudio
import wave
import speech_recognition as sr

filename = "happy.wav"
chunk = 1024
FORMAT = pyaudio.paInt16
channels = 1
sample_rate = 44100
record_seconds = 5

# initialize PyAudio object
p = pyaudio.PyAudio()
                
# initialize the recognizer
r = sr.Recognizer()
                
# open stream object as input & output
stream = p.open(format=FORMAT,
                channels=channels,
                rate=sample_rate,
                input=True,
                output=True,
                frames_per_buffer=chunk)
frames = []
print("Recording...")
for i in range(int(sample_rate / chunk * record_seconds)):
    data = stream.read(chunk)
    frames.append(data)
print("Finished recording.")

stream.stop_stream()
stream.close()

# terminate pyaudio object
p.terminate()

wf = wave.open(filename, "wb")
wf.setnchannels(channels)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(sample_rate)
wf.writeframes(b"".join(frames))
wf.close()
        
with sr.AudioFile(filename) as source:
        audio_data = r.record(source)
        
        # recognize (convert from speech to text)
        text = r.recognize_google(audio_data)
        print(text)
        