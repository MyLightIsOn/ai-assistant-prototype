"""
Multi-agent result synthesis.

Combines outputs from multiple agents into a cohesive final result
by spawning a synthesis subprocess that creates a comprehensive summary.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from claude_interface import execute_claude_task
from logger import get_logger
from .context import read_shared_context

logger = get_logger()


def generate_synthesis_prompt(workspace: Path) -> str:
    """
    Generate synthesis prompt from agent outputs.

    Args:
        workspace: Path to workspace directory

    Returns:
        str: Synthesis prompt for Claude
    """
    # Read shared context
    context = read_shared_context(workspace)

    task_description = context.get("task_description", "No description")
    completed_agents = context.get("completed_agents", [])

    # Build agent outputs section
    agent_outputs = []
    for agent_name in completed_agents:
        if agent_name in context:
            agent_output = context[agent_name]
            agent_outputs.append(
                f"## {agent_name.title()} Agent Output\n"
                + json.dumps(agent_output, indent=2)
            )

    agent_outputs_str = "\n\n".join(agent_outputs) if agent_outputs else "No agent outputs"

    # Generate synthesis prompt
    prompt = f"""# Multi-Agent Task Synthesis

You are synthesizing the results from multiple specialized agents that worked on this task:

**Original Task:**
{task_description}

**Agent Outputs:**
{agent_outputs_str}

---

## Your Mission

Create a cohesive synthesis that:
1. Summarizes what was accomplished across all agents
2. Highlights key achievements and findings
3. Provides actionable recommendations for next steps
4. Identifies any concerns or issues discovered

## Output Requirements

Save your synthesis to `final_result.json` with this structure:

```json
{{
  "summary": "High-level summary of what was accomplished...",
  "key_achievements": [
    "Achievement 1",
    "Achievement 2"
  ],
  "findings": [
    "Important finding 1",
    "Important finding 2"
  ],
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2"
  ],
  "concerns": [
    "Concern 1 (if any)",
    "Concern 2 (if any)"
  ]
}}
```

Focus on creating value by connecting insights across agents and providing a clear, actionable summary.
"""

    return prompt


async def synthesize_results(
    workspace: Path,
    timeout: Optional[int] = 600,  # Default 10 minutes
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Synthesize results from multiple agents into cohesive summary.

    Args:
        workspace: Path to workspace directory
        timeout: Timeout in seconds (default: 600 = 10 minutes)
        max_retries: Maximum retry attempts (default: 3)

    Returns:
        dict: Synthesis result with status and synthesis data
    """
    # Read shared context to check for completed agents
    try:
        context = read_shared_context(workspace)
    except FileNotFoundError:
        return {
            "status": "failed",
            "error": "Shared context not found"
        }

    completed_agents = context.get("completed_agents", [])

    # Validate we have agents to synthesize
    if not completed_agents or len(completed_agents) == 0:
        return {
            "status": "failed",
            "error": "No completed agents to synthesize"
        }

    # Generate synthesis prompt
    try:
        prompt = generate_synthesis_prompt(workspace)
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Failed to generate synthesis prompt: {str(e)}"
        }

    # Retry logic with exponential backoff
    last_error = None
    for attempt in range(max_retries):
        if attempt > 0:
            # Exponential backoff: 1min, 5min, 15min
            backoff_delays = [60, 300, 900]
            delay = backoff_delays[min(attempt - 1, len(backoff_delays) - 1)]
            logger.info(f"Retry attempt {attempt + 1}/{max_retries} for synthesis after {delay}s backoff")
            await asyncio.sleep(delay)

        try:
            start_time = time.time()
            exit_code = 0
            output_lines = []

            logger.info(f"Starting synthesis (attempt {attempt + 1}/{max_retries})")

            # Execute Claude subprocess for synthesis
            async for line in execute_claude_task(
                task_description=prompt,
                workspace_path=str(workspace),
                timeout=timeout
            ):
                output_lines.append(line)

                # Check for exit code
                if "exit code:" in line.lower():
                    try:
                        exit_code = int(line.split("exit code:")[-1].strip().rstrip(")"))
                    except (ValueError, IndexError):
                        pass

            duration_ms = int((time.time() - start_time) * 1000)

            # Parse synthesis output
            synthesis_data = {}
            synthesis_file = workspace / "final_result.json"

            if synthesis_file.exists():
                try:
                    with open(synthesis_file) as f:
                        synthesis_data = json.load(f)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse final_result.json: {e}")
                    # Continue with empty synthesis

            # Check if execution succeeded
            if exit_code == 0:
                logger.info("Synthesis completed successfully")
                return {
                    "status": "completed",
                    "synthesis": synthesis_data,
                    "duration_ms": duration_ms
                }
            else:
                # Non-zero exit code
                error_msg = f"Synthesis exited with code {exit_code}"
                logger.warning(f"Synthesis failed: {error_msg}")

                # If this is the last retry, return failure
                if attempt == max_retries - 1:
                    return {
                        "status": "failed",
                        "error": error_msg,
                        "duration_ms": duration_ms
                    }

                last_error = error_msg
                # Continue to next retry

        except asyncio.TimeoutError:
            error_msg = f"Synthesis timed out after {timeout} seconds"
            logger.error("Synthesis timed out")

            # If this is the last retry, return timeout failure
            if attempt == max_retries - 1:
                return {
                    "status": "failed",
                    "error": error_msg
                }

            last_error = error_msg
            # Continue to next retry

        except Exception as e:
            error_msg = f"Unexpected error during synthesis: {str(e)}"
            logger.error(f"Synthesis error: {e}", exc_info=True)

            # If this is the last retry, return error
            if attempt == max_retries - 1:
                return {
                    "status": "failed",
                    "error": error_msg
                }

            last_error = error_msg
            # Continue to next retry

    # Should never reach here, but just in case
    return {
        "status": "failed",
        "error": last_error or "All synthesis retry attempts failed"
    }
