"""
Multimodal Interview Report Generator.

Generates comprehensive reports combining facial and voice emotion analysis.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# Colors
COLORS = {
    'excellent': '#2ECC71',
    'confident': '#3498DB',
    'moderate': '#F1C40F',
    'nervous': '#E67E22',
    'anxious': '#E74C3C',
    'very_anxious': '#C0392B',
    'facial': '#9B59B6',
    'voice': '#1ABC9C',
    'combined': '#3498DB',
    'background': '#2C3E50',
    'text': '#ECF0F1'
}

EMOTION_COLORS = {
    'happy': '#2ECC71',
    'neutral': '#3498DB',
    'surprise': '#F39C12',
    'sad': '#9B59B6',
    'fear': '#E74C3C',
    'anger': '#C0392B',
    'disgust': '#7F8C8D'
}


def load_session_data(filepath: str) -> Dict:
    """Load session data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def generate_multimodal_report(
    session_data: Dict,
    output_path: str,
    title: str = "Multimodal Interview Analysis Report"
) -> str:
    """
    Generate a comprehensive multimodal report.
    
    Args:
        session_data: Session data dict
        output_path: Path for output PNG
        title: Report title
        
    Returns:
        Path to generated report
    """
    # Extract data
    session_id = session_data['session_id']
    duration = session_data['duration']
    avg_conf = session_data['avg_confidence']
    min_conf = session_data['min_confidence']
    max_conf = session_data['max_confidence']
    begin_conf = session_data['beginning_confidence']
    middle_conf = session_data['middle_confidence']
    end_conf = session_data['end_confidence']
    emotion_dist = session_data['emotion_distribution']
    frames = session_data.get('frames', [])
    
    facial_frames = session_data.get('facial_frames', 0)
    voice_frames = session_data.get('voice_frames', 0)
    multimodal_frames = session_data.get('multimodal_frames', 0)
    total_frames = session_data.get('total_frames', len(frames))
    
    # Create figure
    fig = plt.figure(figsize=(16, 22), facecolor=COLORS['background'])
    gs = GridSpec(6, 2, figure=fig, height_ratios=[0.8, 1.2, 1, 1, 1, 0.8],
                  hspace=0.3, wspace=0.3)
    
    # Title
    fig.suptitle(title, fontsize=24, fontweight='bold', 
                color=COLORS['text'], y=0.98)
    
    # ========== 1. Executive Summary ==========
    ax_summary = fig.add_subplot(gs[0, :])
    ax_summary.set_facecolor(COLORS['background'])
    ax_summary.axis('off')
    
    # Determine overall grade
    if avg_conf >= 80:
        grade = "EXCELLENT"
        grade_color = COLORS['excellent']
    elif avg_conf >= 65:
        grade = "CONFIDENT"
        grade_color = COLORS['confident']
    elif avg_conf >= 50:
        grade = "MODERATE"
        grade_color = COLORS['moderate']
    elif avg_conf >= 35:
        grade = "NERVOUS"
        grade_color = COLORS['nervous']
    else:
        grade = "NEEDS WORK"
        grade_color = COLORS['anxious']
    
    summary_text = f"""
    Session: {session_id}    Duration: {duration:.1f}s    Frames: {total_frames}
    
    OVERALL SCORE: {avg_conf:.1f}%  ({grade})
    Range: {min_conf:.1f}% - {max_conf:.1f}%
    
    Modality Coverage:  Face: {facial_frames}/{total_frames}  |  Voice: {voice_frames}/{total_frames}  |  Both: {multimodal_frames}/{total_frames}
    """
    
    ax_summary.text(0.5, 0.5, summary_text, transform=ax_summary.transAxes,
                   fontsize=14, color=COLORS['text'], ha='center', va='center',
                   family='monospace',
                   bbox=dict(boxstyle='round', facecolor='#34495E', alpha=0.8))
    
    # ========== 2. Confidence Timeline ==========
    ax_timeline = fig.add_subplot(gs[1, :])
    ax_timeline.set_facecolor('#34495E')
    
    if frames:
        timestamps = [(f['timestamp'] - frames[0]['timestamp']) for f in frames]
        confidences = [f['confidence_score'] for f in frames]
        
        # Plot main confidence line
        ax_timeline.plot(timestamps, confidences, color=COLORS['combined'], 
                        linewidth=2, label='Combined', alpha=0.9)
        ax_timeline.fill_between(timestamps, confidences, alpha=0.3, color=COLORS['combined'])
        
        # Plot facial confidence if available
        facial_confs = [f.get('facial_confidence', 0) * 100 for f in frames]
        if any(c > 0 for c in facial_confs):
            ax_timeline.plot(timestamps, facial_confs, color=COLORS['facial'],
                           linewidth=1.5, label='Facial', alpha=0.7, linestyle='--')
        
        # Plot voice confidence if available  
        voice_confs = [f.get('voice_confidence', 0) * 100 for f in frames]
        if any(c > 0 for c in voice_confs):
            ax_timeline.plot(timestamps, voice_confs, color=COLORS['voice'],
                           linewidth=1.5, label='Voice', alpha=0.7, linestyle=':')
        
        # Reference lines
        ax_timeline.axhline(y=65, color=COLORS['confident'], linestyle='--', alpha=0.5, label='Target')
        ax_timeline.axhline(y=avg_conf, color='white', linestyle='-', alpha=0.3, label=f'Avg ({avg_conf:.0f}%)')
    
    ax_timeline.set_xlim(0, duration)
    ax_timeline.set_ylim(0, 100)
    ax_timeline.set_xlabel('Time (seconds)', color=COLORS['text'], fontsize=12)
    ax_timeline.set_ylabel('Confidence %', color=COLORS['text'], fontsize=12)
    ax_timeline.set_title('Confidence Timeline (Multimodal)', color=COLORS['text'], fontsize=14, pad=10)
    ax_timeline.legend(loc='upper right', facecolor='#34495E', edgecolor='white', labelcolor=COLORS['text'])
    ax_timeline.tick_params(colors=COLORS['text'])
    ax_timeline.grid(True, alpha=0.2)
    
    # ========== 3. Segment Comparison ==========
    ax_segments = fig.add_subplot(gs[2, 0])
    ax_segments.set_facecolor('#34495E')
    
    segments = ['Beginning\n(0-20%)', 'Middle\n(20-80%)', 'End\n(80-100%)']
    segment_values = [begin_conf, middle_conf, end_conf]
    segment_colors = [COLORS['anxious'] if v < 50 else COLORS['moderate'] if v < 65 else COLORS['confident'] 
                     for v in segment_values]
    
    bars = ax_segments.bar(segments, segment_values, color=segment_colors, edgecolor='white', linewidth=2)
    
    # Add value labels
    for bar, val in zip(bars, segment_values):
        ax_segments.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                        f'{val:.1f}%', ha='center', color=COLORS['text'], fontsize=12, fontweight='bold')
    
    # Growth arrow
    growth = end_conf - begin_conf
    growth_text = f"Growth: {'+' if growth >= 0 else ''}{growth:.1f}%"
    growth_color = COLORS['excellent'] if growth > 0 else COLORS['anxious']
    ax_segments.text(0.5, 0.95, growth_text, transform=ax_segments.transAxes,
                    ha='center', color=growth_color, fontsize=14, fontweight='bold')
    
    ax_segments.set_ylim(0, 100)
    ax_segments.set_ylabel('Confidence %', color=COLORS['text'])
    ax_segments.set_title('Segment Analysis', color=COLORS['text'], fontsize=14, pad=10)
    ax_segments.tick_params(colors=COLORS['text'])
    
    # ========== 4. Emotion Distribution ==========
    ax_emotions = fig.add_subplot(gs[2, 1])
    ax_emotions.set_facecolor('#34495E')
    
    if emotion_dist:
        emotions = list(emotion_dist.keys())
        percentages = list(emotion_dist.values())
        colors = [EMOTION_COLORS.get(e, '#7F8C8D') for e in emotions]
        
        wedges, texts, autotexts = ax_emotions.pie(
            percentages, labels=emotions, colors=colors,
            autopct='%1.1f%%', pctdistance=0.75,
            wedgeprops=dict(width=0.5, edgecolor='white'),
            textprops=dict(color=COLORS['text'])
        )
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
    
    ax_emotions.set_title('Emotion Distribution', color=COLORS['text'], fontsize=14, pad=10)
    
    # ========== 5. Modality Comparison ==========
    ax_modality = fig.add_subplot(gs[3, 0])
    ax_modality.set_facecolor('#34495E')
    
    if frames:
        # Get average emotions per modality
        facial_emotions = {}
        voice_emotions = {}
        
        for f in frames:
            if f.get('facial_emotions'):
                for e, v in f['facial_emotions'].items():
                    facial_emotions[e] = facial_emotions.get(e, []) + [v]
            if f.get('voice_emotions'):
                for e, v in f['voice_emotions'].items():
                    voice_emotions[e] = voice_emotions.get(e, []) + [v]
        
        # Average them
        all_emotions = set(list(facial_emotions.keys()) + list(voice_emotions.keys()))
        
        if all_emotions:
            x = np.arange(len(all_emotions))
            width = 0.35
            
            facial_avg = [np.mean(facial_emotions.get(e, [0])) * 100 for e in all_emotions]
            voice_avg = [np.mean(voice_emotions.get(e, [0])) * 100 for e in all_emotions]
            
            ax_modality.bar(x - width/2, facial_avg, width, label='Facial', color=COLORS['facial'], alpha=0.8)
            ax_modality.bar(x + width/2, voice_avg, width, label='Voice', color=COLORS['voice'], alpha=0.8)
            
            ax_modality.set_xticks(x)
            ax_modality.set_xticklabels(all_emotions, rotation=45, ha='right')
            ax_modality.legend(facecolor='#34495E', edgecolor='white', labelcolor=COLORS['text'])
    
    ax_modality.set_ylabel('Average Probability %', color=COLORS['text'])
    ax_modality.set_title('Facial vs Voice Emotions', color=COLORS['text'], fontsize=14, pad=10)
    ax_modality.tick_params(colors=COLORS['text'])
    
    # ========== 6. Modality Coverage ==========
    ax_coverage = fig.add_subplot(gs[3, 1])
    ax_coverage.set_facecolor('#34495E')
    
    coverage_labels = ['Face Only', 'Voice Only', 'Both', 'Neither']
    face_only = facial_frames - multimodal_frames
    voice_only = voice_frames - multimodal_frames
    neither = total_frames - facial_frames - voice_only
    coverage_values = [max(0, face_only), max(0, voice_only), multimodal_frames, max(0, neither)]
    coverage_colors = [COLORS['facial'], COLORS['voice'], COLORS['excellent'], '#7F8C8D']
    
    # Filter out zeros
    non_zero = [(l, v, c) for l, v, c in zip(coverage_labels, coverage_values, coverage_colors) if v > 0]
    if non_zero:
        labels, values, colors = zip(*non_zero)
        ax_coverage.pie(values, labels=labels, colors=colors, autopct='%1.0f%%',
                       textprops=dict(color=COLORS['text']),
                       wedgeprops=dict(edgecolor='white'))
    
    ax_coverage.set_title('Modality Coverage', color=COLORS['text'], fontsize=14, pad=10)
    
    # ========== 7. Dominant Emotion Timeline ==========
    ax_emotion_time = fig.add_subplot(gs[4, :])
    ax_emotion_time.set_facecolor('#34495E')
    
    if frames:
        timestamps = [(f['timestamp'] - frames[0]['timestamp']) for f in frames]
        dominant_emotions = [f.get('dominant_emotion', 'neutral') for f in frames]
        
        # Create scatter plot colored by emotion
        unique_emotions = list(set(dominant_emotions))
        for emotion in unique_emotions:
            mask = [e == emotion for e in dominant_emotions]
            times = [t for t, m in zip(timestamps, mask) if m]
            y_vals = [unique_emotions.index(emotion) for _ in times]
            color = EMOTION_COLORS.get(emotion, '#7F8C8D')
            ax_emotion_time.scatter(times, y_vals, c=color, label=emotion, s=30, alpha=0.7)
        
        ax_emotion_time.set_yticks(range(len(unique_emotions)))
        ax_emotion_time.set_yticklabels(unique_emotions)
        ax_emotion_time.legend(loc='upper right', facecolor='#34495E', 
                               edgecolor='white', labelcolor=COLORS['text'], ncol=3)
    
    ax_emotion_time.set_xlim(0, duration)
    ax_emotion_time.set_xlabel('Time (seconds)', color=COLORS['text'])
    ax_emotion_time.set_title('Dominant Emotion Over Time', color=COLORS['text'], fontsize=14, pad=10)
    ax_emotion_time.tick_params(colors=COLORS['text'])
    ax_emotion_time.grid(True, alpha=0.2, axis='x')
    
    # ========== 8. Recommendations ==========
    ax_recs = fig.add_subplot(gs[5, :])
    ax_recs.set_facecolor(COLORS['background'])
    ax_recs.axis('off')
    
    # Generate recommendations
    recs = []
    
    if avg_conf < 50:
        recs.append("• Practice relaxation techniques before interviews")
    if begin_conf < end_conf - 10:
        recs.append("• Work on starting stronger - first impressions matter!")
    if end_conf < begin_conf - 10:
        recs.append("• Maintain energy throughout - don't fade at the end")
    if emotion_dist.get('fear', 0) > 20 or emotion_dist.get('anger', 0) > 15:
        recs.append("• Focus on managing stress signals")
    if multimodal_frames < total_frames * 0.5:
        recs.append("• Ensure good lighting and clear audio for better analysis")
    if emotion_dist.get('happy', 0) < 10:
        recs.append("• Try to incorporate more genuine smiles")
    if not recs:
        recs.append("• Great job! Keep practicing to maintain your confidence")
    
    rec_text = "RECOMMENDATIONS\n\n" + "\n".join(recs)
    ax_recs.text(0.5, 0.5, rec_text, transform=ax_recs.transAxes,
                fontsize=12, color=COLORS['text'], ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='#34495E', alpha=0.8))
    
    # Save
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=150, facecolor=COLORS['background'],
                bbox_inches='tight', pad_inches=0.5)
    plt.close()
    
    print(f"📊 Report saved: {output_path}")
    return output_path


def generate_text_report(session_data: Dict, output_path: str) -> str:
    """Generate detailed text report."""
    
    lines = []
    lines.append("=" * 70)
    lines.append("           Q&ACE MULTIMODAL INTERVIEW PERFORMANCE REPORT")
    lines.append("=" * 70)
    lines.append("")
    
    # Session Info
    lines.append("-" * 70)
    lines.append("SESSION INFORMATION")
    lines.append("-" * 70)
    lines.append(f"  Session ID:        {session_data['session_id']}")
    lines.append(f"  Duration:          {session_data['duration']:.1f} seconds")
    lines.append(f"  Total Frames:      {session_data['total_frames']}")
    lines.append("")
    
    # Modality Coverage
    lines.append("-" * 70)
    lines.append("MODALITY COVERAGE")
    lines.append("-" * 70)
    lines.append(f"  Facial Detection:  {session_data['facial_frames']} frames ({session_data['facial_frames']/max(1,session_data['total_frames'])*100:.1f}%)")
    lines.append(f"  Voice Detection:   {session_data['voice_frames']} frames ({session_data['voice_frames']/max(1,session_data['total_frames'])*100:.1f}%)")
    lines.append(f"  Multimodal:        {session_data['multimodal_frames']} frames ({session_data['multimodal_frames']/max(1,session_data['total_frames'])*100:.1f}%)")
    lines.append("")
    
    # Confidence Analysis
    lines.append("-" * 70)
    lines.append("CONFIDENCE ANALYSIS")
    lines.append("-" * 70)
    lines.append(f"  Average:           {session_data['avg_confidence']:.1f}%")
    lines.append(f"  Minimum:           {session_data['min_confidence']:.1f}%")
    lines.append(f"  Maximum:           {session_data['max_confidence']:.1f}%")
    lines.append("")
    lines.append("  Segment Breakdown:")
    lines.append(f"    Beginning:       {session_data['beginning_confidence']:.1f}%")
    lines.append(f"    Middle:          {session_data['middle_confidence']:.1f}%")
    lines.append(f"    End:             {session_data['end_confidence']:.1f}%")
    
    growth = session_data['end_confidence'] - session_data['beginning_confidence']
    lines.append(f"    Growth:          {'+' if growth >= 0 else ''}{growth:.1f}%")
    lines.append("")
    
    # Emotion Distribution
    lines.append("-" * 70)
    lines.append("EMOTION DISTRIBUTION")
    lines.append("-" * 70)
    for emotion, pct in sorted(session_data['emotion_distribution'].items(), 
                               key=lambda x: x[1], reverse=True):
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        lines.append(f"  {emotion:12s}: {pct:5.1f}% [{bar}]")
    lines.append("")
    
    lines.append("=" * 70)
    lines.append("                    END OF REPORT")
    lines.append("=" * 70)
    
    report_text = "\n".join(lines)
    
    with open(output_path, 'w') as f:
        f.write(report_text)
    
    print(f"📝 Text report saved: {output_path}")
    return output_path


def generate_reports(session_data: Dict, output_dir: str) -> Dict[str, str]:
    """
    Generate both visual and text reports.
    
    Args:
        session_data: Session data dict
        output_dir: Output directory
        
    Returns:
        Dict with paths to generated reports
    """
    os.makedirs(output_dir, exist_ok=True)
    
    session_id = session_data['session_id']
    
    png_path = os.path.join(output_dir, f"multimodal_report_{session_id}.png")
    txt_path = os.path.join(output_dir, f"multimodal_report_{session_id}.txt")
    
    generate_multimodal_report(session_data, png_path)
    generate_text_report(session_data, txt_path)
    
    return {'png': png_path, 'txt': txt_path}


if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        'session_id': 'TEST_MULTIMODAL',
        'duration': 60.0,
        'avg_confidence': 65.5,
        'min_confidence': 42.0,
        'max_confidence': 85.0,
        'beginning_confidence': 55.0,
        'middle_confidence': 65.0,
        'end_confidence': 75.0,
        'emotion_distribution': {
            'neutral': 45.0,
            'happy': 25.0,
            'surprise': 15.0,
            'sad': 8.0,
            'fear': 5.0,
            'anger': 2.0
        },
        'facial_frames': 150,
        'voice_frames': 25,
        'multimodal_frames': 20,
        'total_frames': 180,
        'frames': []
    }
    
    output_dir = "outputs"
    generate_reports(sample_data, output_dir)
