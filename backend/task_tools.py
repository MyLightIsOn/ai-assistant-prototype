"""
Task Management Tool Handlers.

Pure Python functions for task CRUD operations.
Used by both chat_executor.py (direct API) and mcp_task_server.py (MCP protocol).
No MCP dependency - only SQLAlchemy and standard library.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from croniter import croniter
from sqlalchemy.orm import Session

from models import Task, TaskExecution, User

# Resolve templates directory relative to the project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = _PROJECT_ROOT / "ai-workspace" / "templates"


def _sanitize_claude_args(task_args: str, description: str) -> str:
    """
    Sanitize args for claude command tasks.

    The claude CLI args field is passed directly as a prompt to
    `claude --dangerously-skip-permissions --print <args>`.
    If the LLM generates CLI flags (e.g. --repo, --task), strip them
    and rebuild as a plain text prompt.
    """
    if not task_args:
        return description or ""

    if task_args.strip().startswith("--"):
        import shlex
        try:
            tokens = shlex.split(task_args)
        except ValueError:
            tokens = task_args.split()

        urls = []
        instructions = []
        skip_next = False

        for i, token in enumerate(tokens):
            if skip_next:
                skip_next = False
                continue
            if token.startswith("--"):
                flag_name = token.lstrip("-")
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                    value = tokens[i + 1]
                    skip_next = True
                    if flag_name in ("repo", "repository", "url", "project"):
                        urls.append(value)
                    elif flag_name in ("task", "prompt", "instructions", "message"):
                        instructions.append(value)
                    else:
                        instructions.append(f"{flag_name}: {value}")
            else:
                instructions.append(token)

        parts = []
        if urls:
            parts.append(f"Work on the repository at {', '.join(urls)}.")
        if instructions:
            parts.append(" ".join(instructions))
        elif description:
            parts.append(description)

        return " ".join(parts) if parts else description or ""

    return task_args


async def create_task(db: Session, args: dict) -> str:
    """Create a new scheduled task. Returns result message."""
    try:
        name = args["name"]
        description = args.get("description", "")
        command = args.get("command", "claude")
        task_args = args.get("args", "")
        schedule = args["schedule"]
        priority = args.get("priority", "default")
        enabled = args.get("enabled", True)

        # Sanitize args for claude commands
        if command == "claude":
            task_args = _sanitize_claude_args(task_args, description)

        # Get default user
        user = db.query(User).first()
        if not user:
            return "Error: No user found in database. Create a user first."

        # Check for duplicate name
        existing = db.query(Task).filter_by(name=name).first()
        if existing:
            return f"Error: A task named '{name}' already exists (ID: {existing.id}). Please choose a different name or update the existing task."

        # Validate cron schedule
        try:
            croniter(schedule)
        except (ValueError, KeyError) as e:
            return f"Error: Invalid cron schedule '{schedule}': {str(e)}. Example: '0 9 * * *' for 9am daily."

        # Create task
        task = Task(
            userId=user.id,
            name=name,
            description=description,
            command=command,
            args=task_args,
            schedule=schedule,
            priority=priority,
            enabled=enabled,
            createdAt=int(datetime.now(timezone.utc).timestamp() * 1000),
            updatedAt=int(datetime.now(timezone.utc).timestamp() * 1000),
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        # Sync with scheduler so the task gets picked up immediately
        try:
            import requests
            requests.post("http://localhost:8000/api/scheduler/sync", timeout=5)
        except Exception:
            pass  # Non-critical: scheduler will pick it up on next sync/restart

        # Sync with Google Calendar
        try:
            import requests
            requests.post(
                "http://localhost:8000/api/calendar/sync",
                json={"taskId": task.id},
                timeout=5,
            )
        except Exception:
            pass  # Non-critical: calendar sync can be retried manually

        return f"Success: Created task '{task.name}' with ID {task.id}. Schedule: {schedule}"

    except KeyError as e:
        return f"Error: Missing required parameter: {str(e)}"
    except Exception as e:
        db.rollback()
        return f"Error: Failed to create task: {str(e)}"


async def list_tasks(db: Session, args: dict) -> str:
    """List tasks with optional filtering. Returns result message."""
    filter_type = args.get("filter", "all")
    limit = args.get("limit", 50)

    query = db.query(Task)

    if filter_type == "enabled":
        query = query.filter_by(enabled=True)
    elif filter_type == "disabled":
        query = query.filter_by(enabled=False)

    tasks = query.limit(limit).all()

    if not tasks:
        return "No tasks found."

    task_lines = []
    for task in tasks:
        status = "enabled" if task.enabled else "disabled"
        task_lines.append(
            f"- {task.name} (ID: {task.id}) | Schedule: {task.schedule} | Priority: {task.priority} | Status: {status}"
        )

    return f"Found {len(tasks)} task(s):\n" + "\n".join(task_lines)


async def update_task(db: Session, args: dict) -> str:
    """Update an existing task. Returns result message."""
    task_id = args["task_id"]
    updates = args["updates"]

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return f"Error: Task with ID '{task_id}' not found."

    allowed_fields = ["name", "description", "command", "args", "schedule", "priority", "enabled"]
    updated_fields = []

    for field, value in updates.items():
        if field in allowed_fields:
            setattr(task, field, value)
            updated_fields.append(field)

    if not updated_fields:
        return "Error: No valid fields to update."

    task.updatedAt = int(datetime.now(timezone.utc).timestamp() * 1000)
    db.commit()

    # Sync with Google Calendar
    try:
        import requests
        requests.post(
            "http://localhost:8000/api/calendar/sync",
            json={"taskId": task_id},
            timeout=5,
        )
    except Exception:
        pass  # Non-critical: calendar sync can be retried manually

    return f"Success: Updated task '{task.name}' (ID: {task_id}). Updated fields: {', '.join(updated_fields)}"


async def delete_task(db: Session, args: dict) -> str:
    """Delete a task. Returns result message."""
    task_id = args["task_id"]

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return f"Error: Task with ID '{task_id}' not found."

    task_name = task.name

    # Delete Google Calendar event first
    try:
        import requests
        requests.delete(
            f"http://localhost:8000/api/calendar/sync/{task_id}",
            timeout=5,
        )
    except Exception:
        pass  # Non-critical: orphaned calendar events can be cleaned up manually

    db.delete(task)
    db.commit()

    return f"Success: Deleted task '{task_name}' (ID: {task_id})."


async def execute_task(db: Session, args: dict) -> str:
    """Execute a task immediately. Returns result message."""
    task_id = args["task_id"]

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return f"Error: Task with ID '{task_id}' not found."

    return f"Task '{task.name}' (ID: {task_id}) has been queued for immediate execution."


async def get_task_executions(db: Session, args: dict) -> str:
    """Get execution history for a task. Returns result message."""
    task_id = args["task_id"]
    limit = args.get("limit", 10)

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return f"Error: Task with ID '{task_id}' not found."

    executions = (
        db.query(TaskExecution)
        .filter_by(taskId=task_id)
        .order_by(TaskExecution.startedAt.desc())
        .limit(limit)
        .all()
    )

    if not executions:
        return f"No execution history for task '{task.name}'."

    exec_lines = []
    for execution in executions:
        started = datetime.fromtimestamp(execution.startedAt / 1000, tz=timezone.utc)
        status_icon = "completed" if execution.status == "completed" else "failed"
        exec_lines.append(
            f"- {started.strftime('%Y-%m-%d %H:%M:%S')} | Status: {status_icon} | Duration: {execution.duration}ms"
        )

    return f"Last {len(executions)} execution(s) for '{task.name}':\n" + "\n".join(exec_lines)


def _load_template(template_id: str) -> dict:
    """Load a template by ID from the templates directory. Returns dict or raises FileNotFoundError."""
    template_path = TEMPLATES_DIR / f"{template_id}.json"
    if not template_path.exists():
        raise FileNotFoundError(f"Template '{template_id}' not found")
    with open(template_path, "r") as f:
        return json.load(f)


def _build_issue_selection_block(params: dict) -> str:
    """Build the issue selection section of the prompt based on parameters."""
    issues = params.get("issues", "")
    filter_val = params.get("filter", "label:bug")
    max_issues = params.get("max_issues", 3)

    if issues:
        issue_nums = [n.strip() for n in str(issues).split(",") if n.strip()]
        numbered = ", ".join(f"#{n}" for n in issue_nums)
        return f"Fix these specific issues: {numbered}.\nUse `gh issue view <number>` to read each one."
    else:
        return (
            f"Use `gh issue list --label \"{filter_val.replace('label:', '')}\" --limit {max_issues} --state open --json number,title,labels,assignees` "
            f"to find up to {max_issues} open issues.\nSelect issues that look fixable by reading their descriptions."
        )


async def list_templates(db: Session, args: dict) -> str:
    """List available task templates. Returns formatted listing."""
    if not TEMPLATES_DIR.exists():
        return "No templates directory found. No templates available."

    template_files = sorted(TEMPLATES_DIR.glob("*.json"))
    if not template_files:
        return "No templates found."

    lines = []
    for tf in template_files:
        try:
            with open(tf, "r") as f:
                tmpl = json.load(f)
            param_parts = []
            for pname, pdef in tmpl.get("parameters", {}).items():
                req = "(required)" if pdef.get("required") else f"(default: {pdef.get('default', 'none')})"
                param_parts.append(f"  - {pname}: {pdef.get('description', '')} {req}")
            params_str = "\n".join(param_parts) if param_parts else "  (none)"
            lines.append(
                f"**{tmpl['id']}** - {tmpl['name']}\n"
                f"  {tmpl.get('description', '')}\n"
                f"  Default schedule: {tmpl.get('default_schedule', 'none')}\n"
                f"  Parameters:\n{params_str}"
            )
        except (json.JSONDecodeError, KeyError):
            continue

    if not lines:
        return "No valid templates found."

    return f"Available templates ({len(lines)}):\n\n" + "\n\n".join(lines)


async def create_task_from_template(db: Session, args: dict) -> str:
    """Create a task from a template. Validates parameters, substitutes prompt, delegates to create_task."""
    try:
        template_id = args["template_id"]
    except KeyError:
        return "Error: Missing required parameter: template_id"

    try:
        tmpl = _load_template(template_id)
    except FileNotFoundError:
        available = [f.stem for f in TEMPLATES_DIR.glob("*.json")] if TEMPLATES_DIR.exists() else []
        return f"Error: Template '{template_id}' not found. Available: {', '.join(available) or 'none'}"
    except json.JSONDecodeError:
        return f"Error: Template '{template_id}' has invalid JSON."

    params = args.get("parameters", {})
    param_defs = tmpl.get("parameters", {})

    # Validate required parameters
    for pname, pdef in param_defs.items():
        if pdef.get("required") and pname not in params:
            return f"Error: Missing required parameter '{pname}' for template '{template_id}'. Description: {pdef.get('description', '')}"

    # Apply defaults for optional parameters
    for pname, pdef in param_defs.items():
        if pname not in params and "default" in pdef:
            params[pname] = pdef["default"]

    # Build dynamic blocks (only for templates with prompt_template)
    if "prompt_template" in tmpl:
        params["issue_selection_block"] = _build_issue_selection_block(params)

    # Substitute variables into prompt template
    prompt = tmpl.get("prompt_template", "")
    for key, value in params.items():
        prompt = prompt.replace(f"{{{key}}}", str(value))

    # Build task creation args
    task_name = args.get("name", f"{tmpl['name']} - {params.get('repo', template_id)}")
    task_schedule = args.get("schedule", tmpl.get("default_schedule", "0 9 * * 1-5"))
    task_priority = args.get("priority", tmpl.get("default_priority", "default"))

    # Store template provenance in metadata (dict — JSONEncodedText auto-serializes)
    task_metadata = {
        "template_id": template_id,
        "template_name": tmpl.get("name", ""),
        "parameters": params,
    }

    # Merge multi-agent config from template into task metadata
    if "agents" in tmpl:
        agents_config = json.loads(json.dumps(tmpl["agents"]))  # Deep copy
        # Substitute parameter values into agent instruction strings
        for role_name, role_config in agents_config.get("roles", {}).items():
            if "instructions" in role_config:
                for key, value in params.items():
                    role_config["instructions"] = role_config["instructions"].replace(
                        f"{{{key}}}", str(value)
                    )
        task_metadata["agents"] = agents_config

    # Merge email report config from template
    if "email_report" in tmpl:
        email_report = tmpl["email_report"].copy()
        # Substitute parameter values (e.g., {recipient_email})
        for key in list(email_report.keys()):
            if isinstance(email_report[key], str):
                for pname, pvalue in params.items():
                    email_report[key] = email_report[key].replace(
                        f"{{{pname}}}", str(pvalue)
                    )
        task_metadata["email_report"] = email_report

    create_args = {
        "name": task_name,
        "description": tmpl.get("description", ""),
        "command": tmpl.get("command", "claude"),
        "args": prompt if prompt else tmpl.get("description", "Multi-agent task"),
        "schedule": task_schedule,
        "priority": task_priority,
        "enabled": args.get("enabled", True),
    }

    # Delegate to create_task for all validation/sync logic
    result = await create_task(db, create_args)

    # If task was created successfully, update its metadata
    if result.startswith("Success:"):
        # Extract task ID from result message
        try:
            task_id = result.split("ID ")[1].split(".")[0]
            task = db.query(Task).filter_by(id=task_id).first()
            if task:
                task.task_metadata = task_metadata
                db.commit()
        except (IndexError, Exception):
            pass  # Non-critical: metadata is supplementary

    return result
