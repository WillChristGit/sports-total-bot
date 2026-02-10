# Recursive Language Model (RLM) Implementation

Based on arXiv:2512.24601 - "Recursive Language Models"

## What It Does

RLM allows SportsTotalBot to analyze **arbitrarily large sports datasets** beyond LLM context window limits by:

1. **Decomposing** large data into manageable chunks
2. **Recursively processing** each chunk
3. **Synthesizing** results into final recommendations

This means you can feed entire seasons, millions of tokens of stats, and get comprehensive analysis.

---

## Quick Start

### 1. Install Dependencies

```bash
pip install anthropic  # For Claude (optional)
# GLM uses existing `requests` library
```

### 2. Set API Key

```bash
# Edit .env file
GLM_API_KEY=your_glm_api_key_here

# Or use Claude
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 3. Run Test

```bash
# Test with GLM (default)
python test_rlm_analyzer.py

# Test with Claude
python test_rlm_analyzer.py --provider claude

# Test with large dataset
python test_rlm_analyzer.py --test large

# Test with real cached data
python test_rlm_analyzer.py --test real
```

---

## Usage Examples

### Basic Analysis

```python
from src.analysis.recursive_analyzer import create_analyzer
from src.data.models import Game, TeamStats

# Create analyzer
analyzer = create_analyzer(provider="glm")

# Analyze games (can handle 1000+ games)
result = analyzer.analyze_games(
    games=games_list,
    team_stats=team_stats_dict,
    task="find_betting_edges"
)

# Get recommendations
for rec in result.recommendations:
    print(f"{rec.game_id}: {rec.bet_type} {rec.side} @ {rec.line}")
    print(f"  EV: {rec.ev:.1%}, Confidence: {rec.confidence:.1%}")
```

### Season Analysis

```python
# Analyze entire season
result = analyzer.analyze_season(
    season_data={
        "games": all_2025_26_games,  # Can be massive
        "team_stats": full_season_stats,
        "injuries": injury_data
    },
    task="season_betting_analysis"
)

print(result.reasoning)
```

### Custom Configuration

```python
from src.analysis.recursive_analyzer import RecursiveAnalyzer, RLMConfig

config = RLMConfig(
    provider="claude",  # or "glm", "openai"
    max_chunk_size=100000,  # Larger chunks = fewer API calls
    max_depth=15,
    temperature=0.5,
    estimated_cost_limit=10.0  # Stop at $10
)

analyzer = RecursiveAnalyzer(config)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  RecursiveAnalyzer                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Input: Large Dataset (1M+ tokens)                      │
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                   │
│  │  Check Size     │                                   │
│  └────────┬────────┘                                   │
│           │                                             │
│     ┌─────┴─────┐                                       │
│     ▼           ▼                                       │
│  [Small]    [Large]                                     │
│     │           │                                       │
│     │       ┌───┴────┐                                 │
│     │       │ Split  │                                 │
│     │       └───┬────┘                                 │
│     │           │                                       │
│     │      ┌────┴────┐                                 │
│     │      ▼         ▼                                 │
│     │   Chunk1   Chunk2   ...                         │
│     │      │         │                                 │
│     │      └───┬─────┘                                 │
│     │          ▼                                        │
│     │   [Recursive Call]                               │
│     │          │                                        │
│     │          ▼                                        │
│     │   Process Each Chunk                             │
│     │          │                                        │
│     │          ▼                                        │
│     │   ┌───────────────┐                              │
│     │   │  Synthesize   │                              │
│     │   │  Results      │                              │
│     │   └───────┬───────┘                              │
│     │           │                                        │
│     └───────────┴─────────────────────────────────────┘
│                 │
│                 ▼
│         Final Recommendations
│         ─────────────────────
│         • Top 3-5 bets
│         • EV and confidence
│         • Detailed reasoning
│         • Cost tracking
└─────────────────────────────────────────────────────────┘
```

---

## Cost Estimates

| Provider | Input Cost | Output Cost | Typical Analysis (50 games) |
|----------|-----------|-------------|------------------------------|
| GLM-4-Plus | ~$0.50/M | ~$0.50/M | ~$0.02-$0.05 |
| Claude Sonnet 4.5 | $3/M | $15/M | ~$0.10-$0.30 |
| GPT-4o | $2.50/M | $10/M | ~$0.05-$0.15 |

**Season analysis (1000 games):** ~$0.10-$1.00 depending on provider

---

## Files Structure

```
SportsTotalBot/
├── src/
│   ├── analysis/
│   │   └── recursive_analyzer.py  # RLM engine
│   └── utils/
│       └── llm_client.py          # LLM API client
├── test_rlm_analyzer.py           # Test/demo script
├── requirements.txt               # Updated with anthropic
├── .env.example                   # Updated with GLM key
└── RLM_README.md                  # This file
```

---

## Integration with Existing Bot

To use RLM in your main bot:

```python
# main_v2.py

from src.analysis.recursive_analyzer import create_analyzer

# Initialize RLM analyzer
rlm_analyzer = create_analyzer(provider="glm")

def generate_picks_with_rlm(games, stats):
    """Generate picks using RLM for deep analysis"""

    # Use existing analysis for basic projections
    basic_picks = analyze_games_traditional(games, stats)

    # Use RLM for enhanced analysis
    if len(games) > 20:  # Worth RLM for larger datasets
        rlm_result = rlm_analyzer.analyze_games(
            games=games,
            team_stats=stats,
            task="find_betting_edges"
        )

        # Combine results
        enhanced_picks = merge_picks(basic_picks, rlm_result.recommendations)
        return enhanced_picks

    return basic_picks
```

---

## Performance

The RLM implementation can handle:

- **100 games** in ~10-30 seconds
- **1,000 games** in ~1-3 minutes
- **10,000+ games** with deeper recursion

Typical resource usage:
- Memory: <500MB for most analyses
- API calls: 2-10 depending on data size
- Cost: $0.01-$1.00 per analysis

---

## Troubleshooting

**GLM API Key Not Found:**
```bash
export GLM_API_KEY="your_key_here"
# or add to .env file
```

**Import Error for anthropic:**
```bash
pip install anthropic
# or use provider="glm" instead
```

**Analysis Too Slow:**
- Increase `max_chunk_size` in config
- Reduce input data size
- Use faster provider (GLM is fastest)

**Cost Too High:**
- Set `estimated_cost_limit` in config
- Use GLM instead of Claude
- Reduce `max_tokens_per_request`

---

## Future Enhancements

- [ ] Parallel chunk processing
- [ ] Result caching
- [ ] Streaming responses
- [ ] Multi-provider comparison
- [ ] Integration with Telegram alerts

---

## References

- Paper: https://arxiv.org/abs/2512.24601
- Code: https://github.com/alexzhang13/rlm

---

*Last Updated: 2026-02-10*
