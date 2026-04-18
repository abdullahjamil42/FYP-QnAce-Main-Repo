import numpy as np
from app.perception.vocal import analyze_finality

def test_analyze_finality_falling_pitch():
    # Synthetic falling pitch: 200 Hz down to 100 Hz
    fs = 16000
    duration = 1.5
    t = np.linspace(0, duration, int(fs * duration))
    # Frequency falling over time
    f = np.linspace(200, 100, len(t))
    audio = np.sin(2 * np.pi * f * t)
    
    # Add a bit of fade out for energy drop
    fade = np.linspace(1.0, 0.4, len(t))
    audio = (audio * fade).astype(np.float32)
    
    slope, drop = analyze_finality(audio, fs)
    
    # We expect some slope and energy drop
    assert abs(slope) > 0.01 
    assert drop < 1.0

def test_analyze_finality_steady_energy():
    # Steady energy, steady pitch
    fs = 16000
    duration = 1.5
    t = np.linspace(0, duration, int(fs * duration))
    audio = np.sin(2 * np.pi * 200 * t).astype(np.float32)
    
    slope, drop = analyze_finality(audio, fs)
    
    assert abs(slope) < 0.1
    assert abs(drop - 1.0) < 0.1

def test_analyze_finality_short_audio():
    # Less than 0.5s body/tail split
    fs = 16000
    audio = np.zeros(int(0.1 * fs), dtype=np.float32)
    slope, drop = analyze_finality(audio, fs)
    assert slope == 0.0
    assert drop == 1.0
