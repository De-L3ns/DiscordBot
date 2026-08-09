import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src" / "kletserbot"


def _python_imports(source_file: Path) -> tuple[str, ...]:
    tree = ast.parse(source_file.read_text(encoding="utf-8"))
    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)
    return tuple(imported_names)


def test_each_app_obeys_layer_dependencies() -> None:
    apps_root = SOURCE_ROOT / "apps"
    forbidden_external_imports = {"aiohttp", "discord"}

    violations: list[str] = []
    for app_root in apps_root.iterdir():
        if not app_root.is_dir():
            continue
        app_module = f"kletserbot.apps.{app_root.name}"
        for source_file in app_root.rglob("*.py"):
            relative_parts = source_file.relative_to(app_root).parts
            layer = relative_parts[0]
            forbidden_prefixes: tuple[str, ...] = ()
            if layer == "domain":
                forbidden_prefixes = (
                    *forbidden_external_imports,
                    f"{app_module}.application",
                    f"{app_module}.infrastructure",
                    f"{app_module}.presentation",
                )
            elif layer == "application":
                forbidden_prefixes = (
                    *forbidden_external_imports,
                    f"{app_module}.infrastructure",
                    f"{app_module}.presentation",
                )
            elif layer == "presentation":
                forbidden_prefixes = (f"{app_module}.infrastructure",)

            for imported_name in _python_imports(source_file):
                if any(
                    imported_name == prefix or imported_name.startswith(f"{prefix}.")
                    for prefix in forbidden_prefixes
                ):
                    violations.append(f"{source_file.relative_to(PROJECT_ROOT)}: {imported_name}")

    assert violations == []


def test_feature_apps_do_not_import_each_other() -> None:
    violations: list[str] = []
    for source_file in (SOURCE_ROOT / "apps").rglob("*.py"):
        owning_app = source_file.relative_to(SOURCE_ROOT / "apps").parts[0]
        for imported_name in _python_imports(source_file):
            match = re.match(r"kletserbot\.apps\.([^.]+)", imported_name)
            if match and match.group(1) != owning_app:
                violations.append(f"{source_file.relative_to(PROJECT_ROOT)}: {imported_name}")

    assert violations == []


def test_bot_shell_owns_runtime_composition() -> None:
    required_paths = (
        SOURCE_ROOT / "bot" / "application_settings.py",
        SOURCE_ROOT / "bot" / "bot_factory.py",
        SOURCE_ROOT / "bot" / "discord_bot.py",
    )

    assert [path for path in required_paths if not path.exists()] == []


def test_horizontal_layer_packages_are_removed() -> None:
    obsolete_roots = (
        SOURCE_ROOT / "presentation",
        SOURCE_ROOT / "application",
        SOURCE_ROOT / "domain",
        SOURCE_ROOT / "infrastructure",
    )
    remaining_source_files = [
        source_file
        for obsolete_root in obsolete_roots
        for source_file in obsolete_root.rglob("*.py")
    ]

    assert remaining_source_files == []


def test_root_readme_links_global_and_app_documentation() -> None:
    root_readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    required_links = (
        "docs/architecture/README.md",
        "docs/setup.md",
        "src/kletserbot/apps/general/docs/README.md",
        "src/kletserbot/apps/cardpacks/docs/README.md",
        "src/kletserbot/apps/wielermanager/docs/README.md",
    )

    assert [link for link in required_links if link not in root_readme] == []


def test_general_feature_is_owned_by_general_app() -> None:
    general_root = SOURCE_ROOT / "apps" / "general"
    required_paths = (
        general_root / "presentation" / "discord" / "birthdays_cog.py",
        general_root / "presentation" / "discord" / "general_cog.py",
        general_root / "presentation" / "discord" / "reaction_roles_cog.py",
        general_root / "application" / "birthdays" / "birthday_service.py",
        general_root / "application" / "nostalgia" / "nostalgia_service.py",
        general_root / "application" / "quotes" / "quote_service.py",
        general_root / "application" / "reaction_roles" / "reaction_role_service.py",
        general_root / "domain" / "birthdays" / "birthday.py",
        general_root / "infrastructure" / "imgur" / "imgur_album_client.py",
        general_root / "infrastructure" / "static_content" / "static_quote_provider.py",
        general_root / "docs" / "README.md",
        general_root / "docs" / "features" / "README.md",
        general_root / "docs" / "decision-log" / "README.md",
    )

    assert [path for path in required_paths if not path.exists()] == []


def test_cardpacks_feature_is_owned_by_cardpacks_app() -> None:
    cardpacks_root = SOURCE_ROOT / "apps" / "cardpacks"
    required_paths = (
        cardpacks_root / "presentation" / "discord" / "cardpacks_cog.py",
        cardpacks_root / "presentation" / "discord" / "cardpack_views.py",
        cardpacks_root / "application" / "cardpack_service.py",
        cardpacks_root / "application" / "exceptions.py",
        cardpacks_root / "domain" / "pack_generator.py",
        cardpacks_root / "infrastructure" / "pokemon_tcg_client.py",
        cardpacks_root / "infrastructure" / "config" / "sets.json",
        cardpacks_root / "assets" / "discord" / "kletserbot-card-back.png",
        cardpacks_root / "docs" / "README.md",
        cardpacks_root / "docs" / "features" / "README.md",
        cardpacks_root / "docs" / "decision-log" / "README.md",
    )

    assert [path for path in required_paths if not path.exists()] == []


def test_wielermanager_feature_is_owned_by_wielermanager_app() -> None:
    app_root = SOURCE_ROOT / "apps" / "wielermanager"
    required_paths = (
        app_root / "presentation" / "discord" / "wielermanager_cog.py",
        app_root / "presentation" / "discord" / "response_formatter.py",
        app_root / "application" / "wielermanager_service.py",
        app_root / "domain" / "cycling_leaderboard.py",
        app_root / "infrastructure" / "sporza" / "sporza_cycling_client.py",
        app_root / "docs" / "README.md",
        app_root / "docs" / "features" / "README.md",
        app_root / "docs" / "decision-log" / "README.md",
    )

    assert [path for path in required_paths if not path.exists()] == []


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

    assert requirements == {"aiohttp", "discord.py", "python-dotenv", "tzdata"}


def test_dockerfile_targets_python_312_and_non_root_user() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.startswith("FROM python:3.12")
    assert "\nUSER kletserbot\n" in dockerfile
    assert 'CMD ["python", "-m", "kletserbot"]' in dockerfile


def test_compose_selects_a_runtime_environment_file() -> None:
    compose_file = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "env_file:" in compose_file
    assert "${KLETSERBOT_ENV_FILE:-.env}" in compose_file
    assert "restart: unless-stopped" in compose_file


def test_compose_persists_cardpack_data_in_named_volume() -> None:
    compose_file = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "cardpack-data:/app/data/cardpacks" in compose_file
    assert "\nvolumes:\n  cardpack-data:\n" in compose_file
    assert "${CARDPACK_DATA_VOLUME:-kletserbot-cardpack-data}" in compose_file


def test_compose_waits_for_discord_readiness() -> None:
    compose_file = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "healthcheck:" in compose_file
    assert "/tmp/kletserbot-ready" in compose_file


def test_dockerfile_prepares_non_root_cardpack_data_directory() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "mkdir --parents /app/data/cardpacks" in dockerfile
    assert "chown kletserbot:kletserbot /app/data/cardpacks" in dockerfile


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
