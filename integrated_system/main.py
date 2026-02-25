#!/usr/bin/env python3
"""
Q&ACE Multimodal Interview Analyzer - Main Entry Point

Usage:
    python main.py              # Run real-time analysis
    python main.py --test       # Run system tests
    python main.py --report     # Generate sample report
"""

import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="Q&ACE Multimodal Interview Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Run real-time interview analysis
  python main.py --test             Run system tests
  python main.py --report           Generate a sample report
  python main.py --facial-only      Use facial detection only
  python main.py --voice-only       Use voice detection only
        """
    )
    
    parser.add_argument('--test', action='store_true',
                       help='Run system tests')
    parser.add_argument('--report', action='store_true',
                       help='Generate sample report')
    parser.add_argument('--facial-only', action='store_true',
                       help='Use facial detection only')
    parser.add_argument('--voice-only', action='store_true',
                       help='Use voice detection only')
    parser.add_argument('--facial-weight', type=float, default=0.5,
                       help='Weight for facial emotions (0-1)')
    parser.add_argument('--voice-weight', type=float, default=0.5,
                       help='Weight for voice emotions (0-1)')
    
    args = parser.parse_args()
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ██████╗  ██╗   ██╗ █████╗  █████╗ ███████╗              ║
    ║  ██╔═══██╗██║   ██║██╔══██╗██╔══██╗██╔════╝              ║
    ║  ██║   ██║██║   ██║███████║██║  ╚═╝█████╗                ║
    ║  ██║▄▄ ██║██║   ██║██╔══██║██║  ██╗██╔══╝                ║
    ║  ╚██████╔╝╚██████╔╝██║  ██║╚█████╔╝███████╗              ║
    ║   ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝ ╚════╝ ╚══════╝              ║
    ║                                                           ║
    ║         Multimodal Interview Emotion Analyzer             ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    if args.test:
        # Run tests
        from test_system import main as run_tests
        run_tests()
        
    elif args.report:
        # Generate sample report
        from report_generator import generate_reports
        
        sample_data = {
            'session_id': 'SAMPLE_REPORT',
            'duration': 60.0,
            'avg_confidence': 68.5,
            'min_confidence': 45.0,
            'max_confidence': 88.0,
            'beginning_confidence': 58.0,
            'middle_confidence': 68.0,
            'end_confidence': 78.0,
            'emotion_distribution': {
                'neutral': 42.0,
                'happy': 28.0,
                'surprise': 12.0,
                'sad': 8.0,
                'fear': 6.0,
                'anger': 4.0
            },
            'facial_frames': 150,
            'voice_frames': 25,
            'multimodal_frames': 20,
            'total_frames': 180,
            'frames': []
        }
        
        output_dir = "outputs"
        reports = generate_reports(sample_data, output_dir)
        print(f"\n✅ Sample reports generated!")
        print(f"   PNG: {reports['png']}")
        print(f"   TXT: {reports['txt']}")
        
    else:
        # Run real-time analysis
        from interview_analyzer import run_realtime_analysis
        
        # Adjust weights if specified
        if args.facial_only:
            print("Mode: Facial detection only")
        elif args.voice_only:
            print("Mode: Voice detection only")
        else:
            print(f"Mode: Multimodal (Facial: {args.facial_weight}, Voice: {args.voice_weight})")
        
        run_realtime_analysis()


if __name__ == "__main__":
    main()
