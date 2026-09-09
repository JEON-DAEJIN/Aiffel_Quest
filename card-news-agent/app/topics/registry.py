from .ai_news import AI_NEWS
from .base import TopicConfig
from .brunch_column_cards import BRUNCH_COLUMN_CARDS
from .voice_instagram_cards import VOICE_COLUMN_CARDS

TOPICS: dict[str, TopicConfig] = {
    AI_NEWS.topic_id: AI_NEWS,
    VOICE_COLUMN_CARDS.topic_id: VOICE_COLUMN_CARDS,
    BRUNCH_COLUMN_CARDS.topic_id: BRUNCH_COLUMN_CARDS,
}


def get_topic(topic_id: str) -> TopicConfig:
    if topic_id not in TOPICS:
        raise KeyError(f"unknown topic_id: {topic_id!r}")
    return TOPICS[topic_id]


def list_topics() -> list[TopicConfig]:
    return list(TOPICS.values())
