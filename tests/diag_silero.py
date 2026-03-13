"""Quick diagnostic: test real Silero VAD model with various audio levels."""
import numpy as np
import onnxruntime as ort

sess = ort.InferenceSession("models/silero-vad/silero_vad.onnx")
inputs = {i.name: i for i in sess.get_inputs()}

print("Model inputs:")
for i in sess.get_inputs():
    print(f"  {i.name}: shape={i.shape}, type={i.type}")
print("Model outputs:")
for o in sess.get_outputs():
    print(f"  {o.name}: shape={o.shape}")

state_shape = tuple(1 if d is None else int(d) for d in inputs["state"].shape)
print(f"State shape resolved: {state_shape}")

state = np.zeros(state_shape, dtype=np.float32)
sr = np.array(16000, dtype=np.int64)
t = np.linspace(0, 512 / 16000, 512)

# Test 1: Silence
print("\n--- Silence ---")
audio = np.zeros((1, 512), dtype=np.float32)
out, state = sess.run(None, {"input": audio, "state": state, "sr": sr})
print(f"prob={float(np.asarray(out).reshape(-1)[0]):.6f}")

# Test 2: 1kHz sine, amplitude 0.5
print("\n--- 1kHz sine, amp=0.5 ---")
audio = (np.sin(2 * np.pi * 1000 * t) * 0.5).astype(np.float32).reshape(1, -1)
out, state = sess.run(None, {"input": audio, "state": state, "sr": sr})
print(f"prob={float(np.asarray(out).reshape(-1)[0]):.6f}")

# Test 3: Simulate int16 RMS=1059 (normalized)
print("\n--- Simulated int16 RMS=1059 ---")
audio = (np.sin(2 * np.pi * 300 * t) * 1059 * np.sqrt(2) / 32768.0).astype(np.float32).reshape(1, -1)
out, state = sess.run(None, {"input": audio, "state": state, "sr": sr})
print(f"prob={float(np.asarray(out).reshape(-1)[0]):.6f}")

# Test 4: Loud speech RMS=5000 — feed multiple chunks
print("\n--- Loud RMS=5000 (5 consecutive chunks) ---")
audio = (np.sin(2 * np.pi * 300 * t) * 5000 * np.sqrt(2) / 32768.0).astype(np.float32).reshape(1, -1)
for i in range(5):
    out, state = sess.run(None, {"input": audio, "state": state, "sr": sr})
    print(f"  chunk {i}: prob={float(np.asarray(out).reshape(-1)[0]):.6f}")

# Test 5: Varying frequency speech chunks
print("\n--- 20 speech chunks varying frequency ---")
state2 = np.zeros(state_shape, dtype=np.float32)
for i in range(20):
    freq = 200 + i * 50
    audio = (np.sin(2 * np.pi * freq * t) * 0.3).astype(np.float32).reshape(1, -1)
    out, state2 = sess.run(None, {"input": audio, "state": state2, "sr": sr})
    print(f"  chunk {i}: freq={freq}Hz prob={float(np.asarray(out).reshape(-1)[0]):.6f}")

# Test 6: Simulate actual WebRTC flow: int16 -> float32 / 32768
print("\n--- Simulated WebRTC int16 audio -> float32/32768 (RMS 2000-6000) ---")
state3 = np.zeros(state_shape, dtype=np.float32)
for rms_target in [500, 1000, 2000, 3000, 5000, 8000, 15000]:
    amp = rms_target * np.sqrt(2)
    raw_i16 = (np.sin(2 * np.pi * 400 * t) * amp).clip(-32768, 32767).astype(np.int16)
    actual_rms = float(np.sqrt(np.mean(raw_i16.astype(np.float32) ** 2)))
    audio = (raw_i16.astype(np.float32) / 32768.0).reshape(1, -1)
    out, state3 = sess.run(None, {"input": audio, "state": state3, "sr": sr})
    p = float(np.asarray(out).reshape(-1)[0])
    print(f"  int16 RMS={actual_rms:.0f} -> prob={p:.6f} {'SPEECH' if p > 0.5 else 'silence'}")
