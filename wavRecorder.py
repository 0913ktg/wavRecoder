from sys import byteorder
from array import array
from struct import pack

import pyaudio
import wave
import os
import pandas as pd
import re
import threading

THRESHOLD = 500
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 44100

def is_silent(snd_data):
    "Returns 'True' if below the 'silent' threshold"
    return max(snd_data) < THRESHOLD

def normalize(snd_data):
    "Average the volume out"
    MAXIMUM = 16384
    times = float(MAXIMUM)/max(abs(i) for i in snd_data)

    r = array('h')
    for i in snd_data:
        r.append(int(i*times))
    return r

def trim(snd_data):
    "Trim the blank spots at the start and end"
    def _trim(snd_data):
        snd_started = False
        r = array('h')

        for i in snd_data:
            if not snd_started and abs(i)>THRESHOLD:
                snd_started = True
                r.append(i)

            elif snd_started:
                r.append(i)
        return r

    # Trim to the left
    snd_data = _trim(snd_data)

    # Trim to the right
    snd_data.reverse()
    snd_data = _trim(snd_data)
    snd_data.reverse()
    return snd_data

def add_silence(snd_data, seconds):
    "Add silence to the start and end of 'snd_data' of length 'seconds' (float)"
    silence = [0] * int(seconds * RATE)
    r = array('h', silence)
    r.extend(snd_data)
    r.extend(silence)
    return r

def record():
    """
    Record a word or words from the microphone and 
    return the data as an array of signed shorts.

    Normalizes the audio, trims silence from the 
    start and end, and pads with 0.5 seconds of 
    blank sound to make sure VLC et al can play 
    it without getting chopped off.
    """
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=1, rate=RATE,
        input=True, output=True,
        frames_per_buffer=CHUNK_SIZE)

    num_silent = 0
    snd_started = False

    r = array('h')

    print('녹음 시작!')
    while 1:
        
        # little endian, signed short
        snd_data = array('h', stream.read(CHUNK_SIZE))
        if byteorder == 'big':
            snd_data.byteswap()
        r.extend(snd_data)

        silent = is_silent(snd_data)

        if silent and snd_started:
            num_silent += 1
        elif not silent and not snd_started:
            snd_started = True
        elif not silent and snd_started:
            num_silent = 0

        if snd_started and num_silent > 30:
            break

    sample_width = p.get_sample_size(FORMAT)
    stream.stop_stream()
    stream.close()
    p.terminate()

    r = normalize(r)
    r = trim(r)
    r = add_silence(r, 0.5)
    return sample_width, r

def record_to_file(path):
    "Records from the microphone and outputs the resulting data to 'path'"
    sample_width, data = record()
    data = pack('<' + ('h'*len(data)), *data)

    wf = wave.open(path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(sample_width)
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()


if __name__ == '__main__':

    data = pd.read_csv('C:/wavRecorder/10000_script_dataset.csv', encoding='utf-8')
    data = data['script'].values.tolist()

    output = []
    hangul = re.compile('[^ ㄱ-ㅣ가-힣]+')

    for s in data:
        output.append(hangul.sub('', s))

    a = 0
    cnt = int(input("시작 인덱스 입력하세요 : "))
    
    while a is not 9:
        a = int(input("녹음 1 , 다시녹음 2 , 나가기 9  ==>  "))
        if a == 1:
            print(f"{output[cnt]}")
            record_to_file(f"recode_output/{cnt}.wav")
            os.system('cls')
            print(f"done - result written to {cnt}.wav")
            cnt += 1

        elif a == 2:
            cnt -= 1
            print(f"{output[cnt]}")
            record_to_file(f"recode_output/{cnt}.wav")
            os.system('cls')
            print(f"done - result written to {cnt}.wav")
            cnt += 1
        else:
            print('제대로입력해주세요')
        
        