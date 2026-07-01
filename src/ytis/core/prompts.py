from __future__ import annotations

from pathlib import Path


def write_analysis_prompt(project_name: str, channel_url: str, output_path: Path) -> None:
    prompt = f"""# YTIS Analysis Prompt

Analyze this YouTube channel transcript research pack.

Project: {project_name}
Channel URL: {channel_url}

Focus on useful, practical intelligence. Do not simply summarize video by video.

Extract:

1. Main audience and customer segment
2. Repeated pain points
3. Business models discussed
4. Offers, services, or products mentioned
5. Step-by-step workflows
6. Repeated frameworks and mental models
7. Tools, platforms, and resources mentioned
8. Claims that need verification
9. Contradictions or weak advice
10. Opportunities relevant to Rafael / Webify
11. Possible service ideas, content ideas, or lead-generation ideas
12. Top videos worth deeper manual review

Output format:

- Executive summary
- Channel positioning
- Key workflows
- Repeated frameworks
- Market/niche signals
- Practical ideas to test
- Evidence notes and uncertainty
"""
    output_path.write_text(prompt, encoding="utf-8")
