import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src" / "kletserbot"


def test_domain_does_not_import_frameworks_or_outer_layers() -> None:
    forbidden_roots = {
        "aiohttp",
        "discord",
        "kletserbot.application",
        "kletserbot.infrastructure",
        "kletserbot.presentation",
    }

    violations: list[str] = []
    for source_file in (SOURCE_ROOT / "domain").rglob("*.py"):
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported_names: list[str] = []
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names = [node.module]
            for imported_name in imported_names:
                if any(
                    imported_name == root or imported_name.startswith(f"{root}.")
                    for root in forbidden_roots
                ):
                    violations.append(f"{source_file.relative_to(PROJECT_ROOT)}: {imported_name}")

    assert violations == []


def test_legacy_runtime_files_are_removed() -> None:
    legacy_paths = (
        "main.py",
        "config/discord_config.py",
        "config/lists.py",
        "models/player_info.py",
        "models/player_table.py",
        "services/sporza_scraper_service.py",
    )

    assert [path for path in legacy_paths if (PROJECT_ROOT / path).exists()] == []


def test_runtime_requirements_contain_only_direct_dependencies() -> None:
    requirements = {
        line.split("==", maxsplit=1)[0]
        for line in (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }

    assert requirements == {"aiohttp", "discord.py", "python-dotenv"}


def test_dockerfile_targets_python_312_and_non_root_user() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.startswith("FROM python:3.12")
    assert "\nUSER kletserbot\n" in dockerfile
    assert 'CMD ["python", "-m", "kletserbot"]' in dockerfile


def test_compose_uses_root_environment_file() -> None:
    compose_file = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "env_file:" in compose_file
    assert "- .env" in compose_file
    assert "restart: unless-stopped" in compose_file


def test_removed_features_are_absent_from_new_source() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in SOURCE_ROOT.rglob("*.py")
    ).lower()

    for removed_name in (
        "remind",
        "vraag",
        "meme",
        "karen",
        "office",
        "de mol",
        "reddit",
        "praw",
    ):
        assert re.search(rf"\b{re.escape(removed_name)}\b", source) is None

    assert "DefaultHelpCommand" not in source
