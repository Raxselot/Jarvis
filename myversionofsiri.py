import sounddevice as sd
import scipy.io.wavfile as wav
import speech_recognition as sr
import requests
import openai
import io
import wave
import pyaudio

class AudioDeviceManager:
    def create_list_of_audio_devices():
        devices = sd.query_devices()
        return [device for device in devices if device['max_input_channels'] > 0]

    def chose_device_from_list(devices):
        print("Verfügbare Mikrofone:")
        for i, device in enumerate(devices):
            print(f"{i}: {device['name']} (Index: {device['index']})")

        selected_device_index = int(input("Gib den Index des gewünschten Mikrofons ein: "))
        for device in devices:
            if device['index'] == selected_device_index:
                print(f"Gewähltes Gerät: {device['name']} (Index: {device['index']})")
                return device['index']

        print("Ungültiger Index. Bitte versuche es erneut.")
        return None

class AudioRecorder:
    def __init__(self, sample_rate, duration, device_index):
        self.sample_rate = sample_rate
        self.duration = duration
        self.device_index = device_index

    def record_audio(self):
        print("Recording...")
        device_info = sd.query_devices(self.device_index, "input")
        channels = device_info['max_input_channels']
        audio = sd.rec(int(self.duration * self.sample_rate), samplerate=self.sample_rate, channels=channels, dtype='int16', device=self.device_index)
        sd.wait()
        return audio

    def save_audio_to_wav(filename, sample_rate, audio_data):
        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]
        wav.write(filename, sample_rate, audio_data)

class SpeechRecognizer:
    def recognize_speech_from_audio(filename):
        recognizer = sr.Recognizer()
        with sr.AudioFile(filename) as source:
            audio = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio, language="de-DE")
        except sr.UnknownValueError:
            print("Entschuldigung, ich konnte das nicht verstehen.")
            return None
        except sr.RequestError as e:
            print(f"Anfragefehler: {e}")
            return None

class OpenAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        openai.api_key = self.api_key

    def send_text_to_openai(self, text):
        payload = {
            'model': 'gpt-4-turbo',
            'messages': [
                {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
                {"role": "user", "content": text}
            ],
            'max_tokens': 3000
        }

        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            },
            json=payload
        )

        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            print("Fehler:", response.text)
            return None

    def speak_text_with_openai(self, text):
        response = requests.post(
            'https://api.openai.com/v1/audio/speech',
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'tts-1',
                'input': text,
                'voice': 'alloy',
                'response_format': 'wav'
            },
            stream=True
        )

        if response.status_code == 200:
            self._play_audio(response)
        else:
            print("Fehler:", response.text)

    def _play_audio(response):
        p = pyaudio.PyAudio()
        CHUNK = 1024

        def play_audio(response):
            wf = wave.open(io.BytesIO(response.content), 'rb')
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)
            data = wf.readframes(CHUNK)
            while data:
                stream.write(data)
                data = wf.readframes(CHUNK)
            stream.stop_stream()
            stream.close()

        play_audio(response)
        p.terminate()

def main():
    api_key = 'yourapikey'
    sample_rate = 44100
    duration = 10
    filename = "output.wav"
    
    audio_device_manager = AudioDeviceManager()
    input_devices = audio_device_manager.create_list_of_audio_devices()
    selected_device_index = audio_device_manager.chose_device_from_list(input_devices)

    if selected_device_index is not None:
        recorder = AudioRecorder(sample_rate, duration, selected_device_index)
        audio_data = recorder.record_audio()
        recorder.save_audio_to_wav(filename, sample_rate, audio_data)

        recognizer = SpeechRecognizer()
        text = recognizer.recognize_speech_from_audio(filename)

        if text:
            print("Sie haben gesagt:", text)
            openai_client = OpenAIClient(api_key)
            response_text = openai_client.send_text_to_openai(text)
            if response_text:
                print("Antwort von ChatGPT:")
                print(response_text)
                openai_client.speak_text_with_openai(response_text)

if __name__ == "__main__":
    main()
