"""
Recommendation Templates for Q&ACE Coaching Pipeline.

This module provides deterministic, template-based recommendations
that work WITHOUT GenAI as a reliable fallback.

Each recommendation includes:
- what_went_well: Positive feedback
- what_to_improve: Actionable improvement suggestion
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class Recommendation:
    """A coaching recommendation."""
    category: str  # 'content', 'voice', 'facial'
    what_went_well: str
    what_to_improve: str
    reason: str  # From diagnosis


class RecommendationTemplates:
    """
    Template-based recommendations for each issue type.
    
    These templates are deterministic and work without GenAI.
    They provide consistent, professional coaching feedback.
    """
    
    # ========================================
    # Content Recommendations
    # ========================================
    CONTENT_TEMPLATES = {
        'lacks_examples': {
            'what_went_well': 'You addressed the question topic and demonstrated understanding of the subject.',
            'what_to_improve': 'Add 1-2 specific examples from your experience using the STAR method (Situation, Task, Action, Result). Concrete examples make your answer memorable and credible.'
        },
        'poor_structure': {
            'what_went_well': 'You provided relevant information about your experience.',
            'what_to_improve': 'Structure your answer using the STAR method: Start with the Situation/context, explain your Task/role, describe the specific Actions you took, and end with measurable Results.'
        },
        'missing_quantification': {
            'what_went_well': 'You explained your approach and reasoning clearly.',
            'what_to_improve': 'Include quantifiable metrics to strengthen impact. Examples: "improved performance by 30%", "reduced costs by $50K", "managed a team of 5", "completed 2 weeks ahead of schedule".'
        },
        'too_brief': {
            'what_went_well': 'You provided a direct, focused answer.',
            'what_to_improve': 'Expand your answer with more context and detail. For behavioral questions, aim for 60-90 seconds of speaking time. Include the situation, your specific actions, and measurable outcomes.'
        },
        'low_relevance': {
            'what_went_well': 'You engaged with the question and provided a response.',
            'what_to_improve': 'Focus more directly on the specific skill or competency being assessed. Before answering, identify the core question and ensure your examples directly demonstrate that skill.'
        },
        'lacks_depth': {
            'what_went_well': 'You covered the basic aspects of the topic.',
            'what_to_improve': 'Add more technical depth and specificity. Explain not just what you did, but why you made those decisions and what you learned from the experience.'
        },
        'off_topic': {
            'what_went_well': 'You demonstrated knowledge in your response.',
            'what_to_improve': 'Stay focused on the specific question asked. If you need a moment to think of a relevant example, it\'s okay to pause briefly rather than giving an off-topic response.'
        },
        'excellent': {
            'what_went_well': 'Excellent response with clear structure, specific examples, and quantifiable outcomes. You demonstrated strong communication skills.',
            'what_to_improve': 'Continue practicing to maintain this level of quality consistently. Consider preparing additional examples for similar questions.'
        }
    }
    
    # ========================================
    # Voice Recommendations
    # ========================================
    VOICE_TEMPLATES = {
        'too_many_fillers': {
            'what_went_well': 'You maintained a natural, conversational tone throughout your response.',
            'what_to_improve': 'Practice replacing filler words (um, uh, like, you know) with brief pauses. Take a breath when you need to think - silence is more professional than fillers.'
        },
        'pace_too_fast': {
            'what_went_well': 'You showed enthusiasm and energy in your delivery.',
            'what_to_improve': 'Slow down your speaking pace, especially during complex explanations. Pause briefly between key points to let important information land with the listener.'
        },
        'pace_too_slow': {
            'what_went_well': 'You spoke clearly and deliberately, which aids comprehension.',
            'what_to_improve': 'Increase your speaking pace slightly to maintain energy and engagement. Practice speaking at a conversational tempo while maintaining clarity.'
        },
        'low_confidence_tone': {
            'what_went_well': 'You completed your answer and addressed the question.',
            'what_to_improve': 'Practice speaking with more conviction. Use a stronger, more confident tone, especially when describing achievements. Record yourself and listen for upward inflections that sound uncertain.'
        },
        'monotone': {
            'what_went_well': 'You maintained a steady, consistent delivery.',
            'what_to_improve': 'Vary your pitch and emphasis to highlight key points. Practice emphasizing important words and using natural energy shifts to maintain listener engagement.'
        },
        'unclear_articulation': {
            'what_went_well': 'You communicated your ideas effectively.',
            'what_to_improve': 'Focus on clear articulation, especially for technical terms. Slow down slightly on important words and ensure you complete each word before moving to the next.'
        },
        'excellent': {
            'what_went_well': 'Clear, confident vocal delivery with appropriate pace, good articulation, and minimal fillers. Your voice projected professionalism.',
            'what_to_improve': 'Maintain this quality by continuing to practice regularly. Consider varying your examples to stay fresh and engaged.'
        }
    }
    
    # ========================================
    # Facial/Non-verbal Recommendations
    # ========================================
    FACIAL_TEMPLATES = {
        'low_engagement': {
            'what_went_well': 'You maintained focus on the camera throughout your response.',
            'what_to_improve': 'Show more facial engagement through natural expressions. Try smiling when appropriate, nodding slightly, and using eyebrow movement to emphasize key points.'
        },
        'anxiety_detected': {
            'what_went_well': 'You completed the interview despite any nervousness.',
            'what_to_improve': 'Practice relaxation techniques before interviews: deep breaths, positive self-talk, and thorough preparation. Remember that some nervousness is normal and can even help performance.'
        },
        'anger_detected': {
            'what_went_well': 'You maintained focus and delivered your response.',
            'what_to_improve': 'Relax your facial muscles, especially around your jaw, forehead, and eyes. Practice speaking with a more relaxed expression - intense focus can sometimes read as tension on camera.'
        },
        'no_eye_contact': {
            'what_went_well': 'You were present and engaged throughout the session.',
            'what_to_improve': 'Maintain eye contact with the camera lens to simulate direct conversation with the interviewer. Position your camera at eye level and avoid looking at notes or secondary screens.'
        },
        'flat_affect': {
            'what_went_well': 'You appeared calm and composed throughout your response.',
            'what_to_improve': 'Add more facial expressiveness to convey enthusiasm. Let your genuine interest in the topic show through - a natural smile when discussing achievements can be very effective.'
        },
        'excellent': {
            'what_went_well': 'Great facial engagement with appropriate expressions, maintained eye contact, and natural energy. You appeared confident and approachable.',
            'what_to_improve': 'Continue practicing to maintain this natural, engaging presence. Your non-verbal communication is a strength.'
        }
    }
    
    def __init__(self):
        """Initialize the recommendation templates."""
        pass
    
    def get_recommendation(
        self, 
        category: str, 
        issue: str,
        reason: str = ""
    ) -> Recommendation:
        """
        Get a template recommendation for an issue.
        
        Args:
            category: 'content', 'voice', or 'facial'
            issue: The specific issue identifier
            reason: The reason from diagnosis (for context)
            
        Returns:
            Recommendation object
        """
        templates = {
            'content': self.CONTENT_TEMPLATES,
            'voice': self.VOICE_TEMPLATES,
            'facial': self.FACIAL_TEMPLATES
        }
        
        category_templates = templates.get(category, {})
        template = category_templates.get(issue, {
            'what_went_well': 'You engaged with the task.',
            'what_to_improve': 'Continue practicing to develop your skills.'
        })
        
        return Recommendation(
            category=category,
            what_went_well=template['what_went_well'],
            what_to_improve=template['what_to_improve'],
            reason=reason
        )
    
    def get_all_recommendations(
        self,
        content_issue: str,
        content_reason: str,
        voice_issue: str,
        voice_reason: str,
        facial_issue: str,
        facial_reason: str
    ) -> Dict[str, Recommendation]:
        """
        Get recommendations for all three categories.
        
        Returns:
            Dictionary with 'content', 'voice', 'facial' recommendations
        """
        return {
            'content': self.get_recommendation('content', content_issue, content_reason),
            'voice': self.get_recommendation('voice', voice_issue, voice_reason),
            'facial': self.get_recommendation('facial', facial_issue, facial_reason)
        }
    
    def format_as_tips(
        self,
        recommendations: Dict[str, Recommendation]
    ) -> Dict[str, Dict[str, str]]:
        """
        Format recommendations as simple tips dictionary.
        
        Returns:
            Dictionary with content_tip, voice_tip, facial_tip
        """
        return {
            'content_tip': {
                'what_went_well': recommendations['content'].what_went_well,
                'what_to_improve': recommendations['content'].what_to_improve,
                'reason': recommendations['content'].reason
            },
            'voice_tip': {
                'what_went_well': recommendations['voice'].what_went_well,
                'what_to_improve': recommendations['voice'].what_to_improve,
                'reason': recommendations['voice'].reason
            },
            'facial_tip': {
                'what_went_well': recommendations['facial'].what_went_well,
                'what_to_improve': recommendations['facial'].what_to_improve,
                'reason': recommendations['facial'].reason
            }
        }


# Global singleton instance
_recommendation_templates: Optional[RecommendationTemplates] = None


def get_recommendation_templates() -> RecommendationTemplates:
    """Get the global recommendation templates instance."""
    global _recommendation_templates
    if _recommendation_templates is None:
        _recommendation_templates = RecommendationTemplates()
    return _recommendation_templates
