"""
Recursive Language Model (RLM) Analyzer for Sports Betting
Based on arXiv:2512.24601 - "Recursive Language Models"

This module implements RLM pattern to analyze arbitrarily large sports datasets
by recursively processing chunks and synthesizing results.
"""

import json
import logging
from typing import Any, List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..utils.llm_client import LLMClient, LLMResponse
from ..data.models import Game, TeamStats, BetRecommendation, SportType


logger = logging.getLogger(__name__)


@dataclass
class RLMConfig:
    """Configuration for RLM analyzer"""
    provider: str = "glm"  # glm, claude, openai
    model: Optional[str] = None
    max_chunk_size: int = 50000  # Characters per chunk
    max_depth: int = 10  # Max recursion depth
    temperature: float = 0.7
    min_confidence: float = 0.55
    min_ev_threshold: float = 0.02

    # Cost tracking
    max_tokens_per_request: int = 8192
    estimated_cost_limit: float = 5.0  # USD

    # Caching
    use_cache: bool = True
    cache_dir: str = "data/rlm_cache"


@dataclass
class RLMResult:
    """Result from RLM analysis"""
    recommendations: List[BetRecommendation] = field(default_factory=list)
    reasoning: str = ""
    chunks_processed: int = 0
    depth_reached: int = 0
    total_tokens_used: int = 0
    estimated_cost: float = 0.0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class RecursiveAnalyzer:
    """
    Recursive Language Model Analyzer for Sports Betting

    Implements the RLM pattern from arXiv:2512.24601 to process
    arbitrarily large sports datasets beyond context window limits.
    """

    def __init__(self, config: Optional[RLMConfig] = None):
        """
        Initialize RLM analyzer

        Args:
            config: RLM configuration (uses defaults if not provided)
        """
        self.config = config or RLMConfig()
        self.llm = LLMClient(provider=self.config.provider, model=self.config.model)

        # Setup cache
        self.cache_dir = Path(self.config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cost tracking
        self.total_tokens = 0
        self.total_cost = 0.0

        logger.info(f"RLM Analyzer initialized with {self.config.provider} ({self.llm.model})")

    def analyze_games(self,
                      games: List[Game],
                      team_stats: Dict[str, TeamStats],
                      odds_data: Optional[Dict] = None,
                      task: str = "find_betting_edges") -> RLMResult:
        """
        Analyze games recursively (handles unlimited game count)

        Args:
            games: List of games to analyze
            team_stats: Team statistics for analysis
            odds_data: Optional odds information
            task: Analysis task description

        Returns:
            RLMResult with recommendations and metadata
        """
        start_time = datetime.now()

        # Prepare data package
        data_package = {
            "games": self._serialize_games(games),
            "team_stats": self._serialize_stats(team_stats),
            "odds": odds_data or {},
            "task": task,
            "timestamp": datetime.now().isoformat()
        }

        # Run recursive analysis
        result = self._recursive_process(
            data=data_package,
            task=task,
            depth=0
        )

        # Record timing
        result.processing_time = (datetime.now() - start_time).total_seconds()
        result.total_tokens_used = self.total_tokens
        result.estimated_cost = self.total_cost

        logger.info(
            f"RLM analysis complete: {len(result.recommendations)} recommendations, "
            f"{result.chunks_processed} chunks, depth {result.depth_reached}, "
            f"cost ${result.estimated_cost:.4f}"
        )

        return result

    def analyze_season(self,
                       season_data: Dict[str, Any],
                       task: str = "season_betting_analysis") -> RLMResult:
        """
        Analyze entire season data recursively

        Args:
            season_data: Full season dataset (can be massive)
            task: Analysis task

        Returns:
            RLMResult with comprehensive analysis
        """
        start_time = datetime.now()

        result = self._recursive_process(
            data=season_data,
            task=task,
            depth=0
        )

        result.processing_time = (datetime.now() - start_time).total_seconds()
        result.total_tokens_used = self.total_tokens
        result.estimated_cost = self.total_cost

        return result

    def _recursive_process(self,
                           data: Any,
                           task: str,
                           depth: int) -> RLMResult:
        """
        Core recursive processing logic

        Args:
            data: Data to process
            task: Task description
            depth: Current recursion depth

        Returns:
            RLMResult
        """
        if depth > self.config.max_depth:
            logger.warning(f"Max depth {self.config.max_depth} exceeded")
            return RLMResult(reasoning="Max depth exceeded")

        # Serialize and check size
        json_str = json.dumps(data, ensure_ascii=False, default=str)
        data_size = len(json_str)

        logger.debug(f"Depth {depth}: Processing {data_size} characters")

        # Base case: Data fits in context window
        if data_size < self.config.max_chunk_size:
            return self._single_api_call(data, task, depth)

        # Recursive case: Split and process
        logger.info(f"Depth {depth}: Data too large ({data_size} chars), splitting...")

        # Smart splitting based on data structure
        chunks = self._smart_split(data, task)
        chunk_results = []

        for i, chunk in enumerate(chunks):
            logger.debug(f"Depth {depth}: Processing chunk {i+1}/{len(chunks)}")
            chunk_result = self._recursive_process(chunk, task, depth + 1)
            chunk_results.append(chunk_result)

        # Synthesize results
        return self._synthesize_results(chunk_results, task, depth)

    def _single_api_call(self,
                         data: Any,
                         task: str,
                         depth: int) -> RLMResult:
        """
        Process data in single API call

        Args:
            data: Data to analyze
            task: Task description
            depth: Current depth

        Returns:
            RLMResult
        """
        prompt = self._build_analysis_prompt(data, task)

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens_per_request
            )

            # Track costs
            self.total_tokens += response.tokens_used or 0
            self.total_cost += response.cost_estimate or 0

            # Parse response
            result = self._parse_llm_response(response.content, task)
            result.depth_reached = depth
            result.chunks_processed = 1

            return result

        except Exception as e:
            logger.error(f"API call failed: {e}")
            return RLMResult(
                reasoning=f"Error: {str(e)}",
                metadata={"error": str(e)}
            )

    def _build_analysis_prompt(self, data: Any, task: str) -> str:
        """Build analysis prompt for LLM"""

        task_prompts = {
            "find_betting_edges": """
Analyze this sports data and identify the best betting opportunities.

For each opportunity, provide:
1. Game ID
2. Bet type (totals, spreads, moneyline)
3. Side (over/under/home/away)
4. Line value
5. Projected value
6. Expected Value (EV) as decimal (e.g., 0.05 = 5%)
7. Win probability (0-1)
8. Confidence level (0-1)
9. Detailed reasoning

Return results as JSON structure with "recommendations" array.
""",
            "season_betting_analysis": """
Analyze this season data and provide:
1. Overall betting trends
2. Most profitable teams/types
3. Key insights and patterns
4. Recommendations for future betting

Return structured analysis with specific actionable insights.
""",
            "default": f"""
Task: {task}

Analyze the provided data and return insights.
Focus on actionable, specific recommendations.
"""
        }

        base_prompt = task_prompts.get(task, task_prompts["default"])

        json_data = json.dumps(data, ensure_ascii=False, default=str, indent=2)

        # Truncate if needed
        if len(json_data) > self.config.max_chunk_size:
            json_data = json_data[:self.config.max_chunk_size] + "\n... [DATA TRUNCATED]"

        return f"""{base_prompt}

DATA:
```json
{json_data}
```

Provide your analysis as structured JSON or clearly formatted text.
"""

    def _smart_split(self, data: Any, task: str) -> List[Any]:
        """
        Intelligently split data based on structure

        Args:
            data: Data to split
            task: Current task (affects splitting strategy)

        Returns:
            List of data chunks
        """
        # If it's a dict with games, split by games
        if isinstance(data, dict) and "games" in data:
            games = data["games"]
            if isinstance(games, list) and len(games) > 10:
                mid = len(games) // 2
                return [
                    {**data, "games": games[:mid]},
                    {**data, "games": games[mid:]}
                ]

        # If it's a list, split in half
        if isinstance(data, list):
            mid = len(data) // 2
            return [data[:mid], data[mid:]]

        # If it's a dict, split keys
        if isinstance(data, dict):
            keys = list(data.keys())
            mid = len(keys) // 2
            return [
                {k: data[k] for k in keys[:mid]},
                {k: data[k] for k in keys[mid:]}
            ]

        # Fallback: string split
        json_str = json.dumps(data, ensure_ascii=False, default=str)
        mid = len(json_str) // 2
        return [json_str[:mid], json_str[mid:]]

    def _synthesize_results(self,
                            chunk_results: List[RLMResult],
                            task: str,
                            depth: int) -> RLMResult:
        """
        Synthesize results from recursive chunks

        Args:
            chunk_results: Results from each chunk
            task: Original task
            depth: Current depth

        Returns:
            Synthesized RLMResult
        """
        # Combine metadata
        total_chunks = sum(r.chunks_processed for r in chunk_results)
        max_depth = max(r.depth_reached for r in chunk_results)

        # Extract recommendations from all chunks
        all_recommendations = []
        for result in chunk_results:
            all_recommendations.extend(result.recommendations)

        # Sort by EV and take top picks
        all_recommendations.sort(key=lambda r: r.ev if hasattr(r, 'ev') else 0, reverse=True)
        top_picks = all_recommendations[:10]  # Keep top 10

        # Build synthesis prompt
        chunk_summaries = []
        for i, result in enumerate(chunk_results):
            summary = {
                "recommendations_count": len(result.recommendations),
                "reasoning": result.reasoning[:500] if result.reasoning else ""
            }
            chunk_summaries.append(summary)

        synthesis_prompt = f"""
You are synthesizing results from {len(chunk_results)} analysis chunks.

TASK: {task}

CHUNK RESULTS:
```json
{json.dumps(chunk_summaries, indent=2)}
```

TOP RECOMMENDATIONS FROM CHUNKS:
```json
{json.dumps([self._rec_to_dict(r) for r in top_picks], indent=2, default=str)}
```

Provide:
1. Final synthesized recommendations (top 3-5)
2. Key insights from across all chunks
3. Confidence levels

Return as structured analysis.
"""

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.3,  # Lower temperature for synthesis
                max_tokens=4096
            )

            self.total_tokens += response.tokens_used or 0
            self.total_cost += response.cost_estimate or 0

            result = self._parse_llm_response(response.content, task)
            result.chunks_processed = total_chunks
            result.depth_reached = max_depth
            result.recommendations = top_picks[:5]  # Final top 5

            return result

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Fallback: return top picks from chunks
            return RLMResult(
                recommendations=top_picks[:5],
                reasoning=f"Synthesis error, returning top chunk picks: {str(e)}",
                chunks_processed=total_chunks,
                depth_reached=max_depth
            )

    def _parse_llm_response(self, response: str, task: str) -> RLMResult:
        """Parse LLM response into RLMResult"""
        result = RLMResult(reasoning=response)

        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                # Extract recommendations
                if "recommendations" in data:
                    for rec in data["recommendations"]:
                        try:
                            result.recommendations.append(self._dict_to_rec(rec))
                        except Exception as e:
                            logger.debug(f"Failed to parse recommendation: {e}")

        except Exception as e:
            logger.debug(f"JSON parsing failed: {e}, using text response")

        return result

    def _rec_to_dict(self, rec: BetRecommendation) -> Dict:
        """Convert BetRecommendation to dict"""
        return {
            "game_id": rec.game_id,
            "sport": rec.sport.value,
            "bet_type": rec.bet_type.value,
            "side": rec.side.value,
            "line": rec.line,
            "odds": rec.odds,
            "projected_value": rec.projected_value,
            "ev": rec.ev,
            "win_probability": rec.win_probability,
            "confidence": rec.confidence,
            "reasoning": rec.reasoning
        }

    def _dict_to_rec(self, data: Dict) -> BetRecommendation:
        """Convert dict to BetRecommendation"""
        return BetRecommendation(
            game_id=data.get("game_id", ""),
            sport=SportType(data.get("sport", "nba")),
            bet_type=data.get("bet_type", "totals"),
            side=data.get("side", "over"),
            line=float(data.get("line", 0)),
            odds=int(data.get("odds", -110)),
            projected_value=float(data.get("projected_value", 0)),
            ev=float(data.get("ev", 0)),
            win_probability=float(data.get("win_probability", 0.5)),
            confidence=float(data.get("confidence", 0.5)),
            reasoning=data.get("reasoning", "")
        )

    def _serialize_games(self, games: List[Game]) -> List[Dict]:
        """Serialize games to dict"""
        return [
            {
                "game_id": g.game_id,
                "sport": g.sport.value,
                "home_team": g.home_team,
                "away_team": g.away_team,
                "game_time": g.game_time.isoformat()
            }
            for g in games
        ]

    def _serialize_stats(self, stats: Dict[str, TeamStats]) -> Dict:
        """Serialize team stats to dict"""
        return {
            team_id: {
                "team_name": s.team_name,
                "games_played": s.games_played,
                "avg_points_scored": s.avg_points_scored,
                "avg_points_allowed": s.avg_points_allowed,
                "offensive_rating": s.offensive_rating,
                "defensive_rating": s.defensive_rating,
                "pace": s.pace
            }
            for team_id, s in stats.items()
        }


def create_analyzer(provider: str = "glm",
                    max_chunk_size: int = 50000,
                    **kwargs) -> RecursiveAnalyzer:
    """
    Factory function to create RLM analyzer

    Args:
        provider: LLM provider ("glm", "claude", "openai")
        max_chunk_size: Max characters per chunk
        **kwargs: Additional config options

    Returns:
        Configured RecursiveAnalyzer
    """
    config = RLMConfig(provider=provider, max_chunk_size=max_chunk_size, **kwargs)
    return RecursiveAnalyzer(config)
