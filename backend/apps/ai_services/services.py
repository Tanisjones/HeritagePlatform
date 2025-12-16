import random

def get_ai_suggestions(heritage_item):
    """
    Mock function to generate AI suggestions for a heritage item.
    In a real implementation, this would call an external AI service.
    """
    suggestions = []

    # Suggest keywords based on description
    if heritage_item.description:
        # A real implementation would use NLP to extract keywords
        keywords = ['historic', 'architecture', 'Riobamba']
        suggestions.append({
            'suggester': 'mock_keyword_extractor',
            'suggestion_type': 'keyword',
            'content': keywords,
            'confidence': random.uniform(0.7, 0.95)
        })

    # Suggest a historical period
    # A real implementation would analyze text and images
    periods = ['colonial', 'republican']
    suggestions.append({
        'suggester': 'mock_period_classifier',
        'suggestion_type': 'historical_period',
        'content': random.choice(periods),
        'confidence': random.uniform(0.6, 0.8)
    })

    return suggestions
