"""生成客户端提示音 ding.wav：双音风铃（E6 -> A6），带衰减，约 0.9 秒。"""
import math
import os
import struct
import wave

RATE = 44100

def tone(freq, start, duration, amp=0.6):
    samples = []
    n0 = int(start * RATE)
    n1 = int((start + duration) * RATE)
    for n in range(n0, n1):
        t = (n - n0) / RATE
        env = math.exp(-4.5 * t) * (1 - math.exp(-80 * t))  # 快起音 + 指数衰减
        v = amp * env * (math.sin(2 * math.pi * freq * t) +
                         0.35 * math.sin(2 * math.pi * freq * 2 * t))
        samples.append((n, v))
    return samples

total = int(1.0 * RATE)
buf = [0.0] * total
for n, v in tone(1318.5, 0.0, 0.9):   # E6
    if n < total:
        buf[n] += v
for n, v in tone(1760.0, 0.18, 0.75, 0.5):  # A6
    if n < total:
        buf[n] += v

frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(v * 32767)))) for v in buf)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DingDong", "Assets", "ding.wav")
os.makedirs(os.path.dirname(out), exist_ok=True)
with wave.open(out, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(frames)
print("written:", out)
