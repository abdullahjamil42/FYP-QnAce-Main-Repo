"""Test Silero with noise and speech-like signals."""
import numpy as np
import onnxruntime as ort

sess = ort.InferenceSession("models/silero-vad/silero_vad.onnx")
inputs = {i.name: i for i in sess.get_inputs()}
state_shape = tuple(1 if d is None else int(d) for d in inputs["state"].shape)

print("=== White noise (broad spectrum, speech-like) ===")
state = np.zeros(state_shape, dtype=np.float32)
sr = np.array(16000, dtype=np.int64)
np.random.seed(42)
for i in range(30):
    noise = (np.random.randn(512) * 0.3).astype(np.float32).reshape(1, -1)
    out, state = sess.run(None, {"input": noise, "state": state, "sr": sr})
    p = float(np.asarray(out).reshape(-1)[0])
    if p > 0.1 or i < 5 or i >= 25:
        print(f"  chunk {i:2d}: prob={p:.6f} {'<< SPEECH' if p > 0.5 else ''}")

print("\n=== Formant-like composite (vowel-like harmonics) ===")
state = np.zeros(state_shape, dtype=np.float32)
t = np.linspace(0, 512 / 16000, 512)
for i in range(30):
    # Simulate vowel: fundamental + harmonics with amplitude shaping
    f0 = 120 + np.random.rand() * 30  # F0 variation
    signal = np.zeros(512, dtype=np.float32)
    for h in range(1, 10):
        amp = 0.3 / h
        signal += amp * np.sin(2 * np.pi * f0 * h * t + np.random.rand() * 6.28)
    # Add some noise
    signal += np.random.randn(512).astype(np.float32) * 0.02
    audio = signal.astype(np.float32).reshape(1, -1)
    out, state = sess.run(None, {"input": audio, "state": state, "sr": sr})
    p = float(np.asarray(out).reshape(-1)[0])
    if p > 0.1 or i < 5 or i >= 25:
        print(f"  chunk {i:2d}: prob={p:.6f} {'<< SPEECH' if p > 0.5 else ''}")

print("\n=== Voice from formant synthesis (F1=500, F2=1500, F3=2500) ===")
state = np.zeros(state_shape, dtype=np.float32)
for i in range(50):
    f0 = 130
    signal = np.zeros(512, dtype=np.float32)
    # Glottal pulse train
    for h in range(1, 20):
        amp = 0.2 * np.exp(-0.1 * h)
        signal += amp * np.sin(2 * np.pi * f0 * h * t + np.random.rand() * 0.1)
    # Add aspiration noise
    signal += np.random.randn(512).astype(np.float32) * 0.05
    audio = signal.astype(np.float32).reshape(1, -1)
    out, state = sess.run(None, {"input": audio, "state": state, "sr": sr})
    p = float(np.asarray(out).reshape(-1)[0])
    if p > 0.1 or i < 5 or i >= 45:
        print(f"  chunk {i:2d}: prob={p:.6f} {'<< SPEECH' if p > 0.5 else ''}")

# Also check: does the model respond at ALL to any input?
print("\n=== Extreme test: constant 1.0, constant -1.0, alternating ===")
state = np.zeros(state_shape, dtype=np.float32)
for label, audio in [
    ("all zeros", np.zeros((1, 512), dtype=np.float32)),
    ("all 1.0", np.ones((1, 512), dtype=np.float32)),
    ("all -1.0", -np.ones((1, 512), dtype=np.float32)),
    ("alternating 1/-1", np.array([1.0 if i % 2 == 0 else -1.0 for i in range(512)], dtype=np.float32).reshape(1, -1)),
]:
    out, state = sess.run(None, {"input": audio, "state": state, "sr": sr})
    p = float(np.asarray(out).reshape(-1)[0])
    print(f"  {label}: prob={p:.6f}")
