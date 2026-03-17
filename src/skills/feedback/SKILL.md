---
name: feedback
description: "Feedback loop learning. Records user sentiment, detects mood, and learns preferences to adapt AI behavior over time."
entry_point: learner.py
---

# Feedback

Enables ASURA to learn and adapt based on direct user interactions. It records user sentiment, identifies preferences through keyword analysis, and stores feedback in semantic memory to refine system prompts and behavioral patterns over time.

### 🔧 Tools / Functions
- `record_feedback(context, feedback, sentiment)`: Log user feedback along with its context and sentiment (positive, negative, or neutral).
- `auto_detect_sentiment(message)`: Analyze message content for emotional keywords to automatically determine sentiment.
- `get_learned_preferences()`: Extract a summary of user likes and dislikes from the feedback history.
- `get_feedback_stats()`: Generate a statistical breakdown of recorded feedback and sentiment distribution.

### 📝 Examples
- "That was a great explanation" -> Sentiment: Positive, Feedback: "That was a great explanation".
- "Stop using f-strings in this file" -> Sentiment: Negative, Feedback recorded for preference learning.

### 🛠️ Requirements
- None (Uses local `feedback.json` for persistence and RAG memory for recall)
