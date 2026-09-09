from .base import TopicConfig

AI_NEWS = TopicConfig(
    topic_id="ai_news",
    display_name="AI 최신소식",
    research_prompt_template=(
        "Search the web for notable AI-related news from the last {lookback_days} days "
        "(measured from today). Return between {min_candidates} and {max_candidates} distinct "
        "candidate stories. For each candidate, include the title, publish date, source URL, "
        "a one-line summary, and a short reason why it is worth choosing for a card-news post.\n\n"
        "If you cannot find at least {min_candidates} solid candidates within {lookback_days} days, "
        "widen your search to the last {expanded_days} days instead, and set expanded_search=true "
        "and search_window_days={expanded_days} in your JSON output. Do not invent candidates or "
        "pad the list with weak or outdated items just to reach the minimum count — report the "
        "number you actually found."
    ),
    image_style_guidance=(
        "clean modern tech illustration, consistent blue-and-white color palette across all "
        "cards, simple flat-design composition, leave empty space near the top for a title overlay"
    ),
)
