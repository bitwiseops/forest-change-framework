"""
Command-line interface commands for the framework.

This module provides CLI commands for interacting with the framework,
including component management, execution, and configuration validation.
"""

import click
import json
from pathlib import Path
import sys
import importlib

from forest_change_framework import (
    BaseFramework,
    get_registry,
    ConfigManager,
    RegistryError,
    ConfigError,
)
from forest_change_framework.utils import setup_logging


def discover_components():
    """
    Auto-discover and import all components.

    Scans the components directory and imports all component modules,
    which triggers their @register_component decorators.
    """
    components_path = Path(__file__).parent.parent / "components"

    if not components_path.exists():
        return

    # Iterate through categories (data_ingestion, preprocessing, etc.)
    for category_dir in components_path.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue

        # Iterate through components within each category
        for component_dir in category_dir.iterdir():
            if not component_dir.is_dir() or component_dir.name.startswith("_"):
                continue

            # Try to import the component module
            try:
                module_path = f"forest_change_framework.components.{category_dir.name}.{component_dir.name}"
                importlib.import_module(module_path)
            except (ImportError, AttributeError) as e:
                # Component may not have a valid module, skip silently
                pass


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--log-file", type=click.Path(), help="Log file path")
@click.pass_context
def cli(ctx, verbose, log_file):
    """Forest Change Framework CLI tool."""
    # Auto-discover components
    discover_components()

    # Setup logging
    import logging

    level = logging.DEBUG if verbose else logging.INFO
    setup_logging("forest_change_framework", level=level, log_file=log_file)

    # Store context
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option(
    "--path",
    type=click.Path(),
    default=".",
    help="Project directory (default: current directory)",
)
@click.option(
    "--name",
    prompt="Project name",
    default="my_forest_project",
    help="Name for the project",
)
def init(path, name):
    """Initialize a new forest change project."""
    try:
        project_path = Path(path) / name
        project_path.mkdir(parents=True, exist_ok=True)

        # Create basic project structure
        (project_path / "data").mkdir(exist_ok=True)
        (project_path / "output").mkdir(exist_ok=True)
        (project_path / "config").mkdir(exist_ok=True)

        # Create sample config file
        config_file = project_path / "config" / "config.json"
        if not config_file.exists():
            default_config = {
                "project": name,
                "data_source": {"type": "csv", "path": "data/input.csv"},
                "processing": {"skip_validation": False},
                "output": {"format": "json", "path": "output/results.json"},
            }
            with open(config_file, "w") as f:
                json.dump(default_config, f, indent=2)

        click.echo(f"✓ Project '{name}' initialized at {project_path}")
        click.echo(f"  - Created data directory")
        click.echo(f"  - Created output directory")
        click.echo(f"  - Created config/config.json")

    except Exception as e:
        click.echo(f"✗ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--category",
    type=str,
    help="Filter by category (optional)",
)
@click.pass_context
def list_components(ctx, category):
    """List all registered components."""
    try:
        registry = get_registry()

        if category:
            components = registry.list_components(category)
            if not components.get(category):
                click.echo(f"No components found in category: {category}")
                return

            click.echo(f"\n📦 Category: {category}")
            for comp_name in components[category]:
                info = registry.get_info(category, comp_name)
                click.echo(f"  • {comp_name} (v{info['version']})")
                if info["description"]:
                    click.echo(f"    {info['description']}")
        else:
            all_components = registry.list_components()

            if not all_components:
                click.echo("No components registered.")
                return

            for cat, comp_list in all_components.items():
                click.echo(f"\n📦 {cat}")
                for comp_name in comp_list:
                    info = registry.get_info(cat, comp_name)
                    click.echo(f"  • {comp_name} (v{info['version']})")
                    if info["description"]:
                        click.echo(f"    {info['description']}")

    except Exception as e:
        click.echo(f"✗ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("category")
@click.argument("component_name")
@click.option("--config", type=click.Path(exists=True), help="Component config file")
@click.pass_context
def run(ctx, category, component_name, config):
    """Run a specific component."""
    try:
        framework = BaseFramework()

        # Load component config if provided
        component_config = {}
        if config:
            try:
                if config.endswith(".json"):
                    with open(config) as f:
                        component_config = json.load(f)
                elif config.endswith(".yaml") or config.endswith(".yml"):
                    try:
                        import yaml

                        with open(config) as f:
                            component_config = yaml.safe_load(f)
                    except ImportError:
                        click.echo("PyYAML required for YAML config", err=True)
                        sys.exit(1)
            except Exception as e:
                click.echo(f"✗ Error loading config: {str(e)}", err=True)
                sys.exit(1)

        # Execute component
        click.echo(f"🚀 Running {category}/{component_name}...")

        result = framework.execute_component(category, component_name, **component_config)

        click.echo(f"✓ Component executed successfully")
        click.echo(f"Result: {result}")

    except RegistryError as e:
        click.echo(f"✗ Component not found: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--schema", type=click.Path(exists=True), help="Validation schema file")
def validate(config_file, schema):
    """Validate a configuration file."""
    try:
        # Load config
        config_manager = ConfigManager.from_json(config_file)
        config_data = config_manager.to_dict()

        if schema:
            # Load schema and validate
            try:
                schema_config = ConfigManager.from_json(schema)
                schema_data = schema_config.to_dict()
                config_manager.validate(schema_data)
                click.echo(f"✓ Configuration is valid according to schema")
            except ConfigError as e:
                click.echo(f"✗ Validation failed: {str(e)}", err=True)
                sys.exit(1)
        else:
            click.echo(f"✓ Configuration file is valid JSON")

        click.echo(f"  Keys: {', '.join(config_data.keys())}")

    except ConfigError as e:
        click.echo(f"✗ Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("category")
@click.argument("component_name")
def info(category, component_name):
    """Show detailed information about a component."""
    try:
        registry = get_registry()
        info_data = registry.get_info(category, component_name)

        click.echo(f"\n📋 Component Information")
        click.echo(f"{'─' * 40}")
        click.echo(f"Name:        {info_data['name']}")
        click.echo(f"Category:    {info_data['category']}")
        click.echo(f"Version:     {info_data['version']}")
        click.echo(f"Description: {info_data['description']}")

        if info_data["metadata"]:
            click.echo(f"\nMetadata:")
            for key, value in info_data["metadata"].items():
                click.echo(f"  {key}: {value}")

    except RegistryError as e:
        click.echo(f"✗ Component not found: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--theme",
    type=click.Choice(["light", "dark"]),
    default="dark",
    help="GUI theme (light or dark)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging in GUI",
)
def gui(theme, debug):
    """Launch the Forest Change Framework GUI application."""
    try:
        from forest_change_framework.gui.app import ForestChangeApp

        app = ForestChangeApp(theme=theme, debug=debug)
        sys.exit(app.run())

    except ImportError as e:
        click.echo(
            "✗ GUI dependencies not installed. Install with:\n"
            "  pip install PyQt6 PyQt6-WebEngine folium matplotlib plotly",
            err=True,
        )
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Failed to launch GUI: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
