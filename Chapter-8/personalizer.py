from openai import OpenAI
from typing import List, Dict
import os

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LEVEL_INSTRUCTIONS = {
    "beginner": "Use simple language, avoid jargon, and explain concepts from scratch.",
    "intermediate": "Assume basic familiarity with the topic. Be clear but not overly simplified.",
    "expert": "Be concise and technical. Skip basics, focus on insights and implications.",
}

TONE_INSTRUCTIONS = {
    "formal": "Write in a professional, objective tone.",
    "casual": "Write in a friendly, conversational tone.",
    "analytical": "Focus on data, cause-effect relationships, and critical evaluation.",
}


def personalize_articles(
    articles: List[Dict],
    user_interests: List[str],
    reading_level: str = "intermediate",
    tone: str = "casual",
) -> List[Dict]:
    level_note = LEVEL_INSTRUCTIONS.get(reading_level, LEVEL_INSTRUCTIONS["intermediate"])
    tone_note = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["casual"])
    interests_str = ", ".join(user_interests)

    personalized = []
    for article in articles:
        try:
            prompt = f"""You are a personal content curator. Given the article below, write a short personalized summary (3-4 sentences) for a reader interested in: {interests_str}.

{level_note}
{tone_note}

Article title: {article['title']}
Article content: {article['summary']}

Write only the personalized summary. No preamble."""

            response = _client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7,
            )

            article["personalized_summary"] = response.choices[0].message.content.strip()
        except Exception as e:
            article["personalized_summary"] = article["summary"]

        personalized.append(article)

    return personalized


def generate_feed_intro(user_name: str, interests: List[str], article_count: int) -> str:
    try:
        response = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": (
                    f"Write a single warm, personalized sentence welcoming {user_name} to their "
                    f"daily content feed. They're interested in: {', '.join(interests)}. "
                    f"There are {article_count} articles ready. Keep it under 25 words."
                ),
            }],
            max_tokens=60,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return f"Here are {article_count} articles curated for you, {user_name}."
