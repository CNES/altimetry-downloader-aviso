import logging
from dataclasses import fields
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

import altimetry_downloader_aviso.core as ac_core
from altimetry_downloader_aviso.catalog_client.client import InvalidProductError

logging.basicConfig(
    level=logging.WARNING, handlers=[RichHandler()], format="%(message)s"
)
logger = logging.getLogger("altimetry_downloader_aviso")


def _setup_logging(quiet: bool = False, verbose: bool = False):
    if quiet and verbose:
        raise typer.BadParameter(
            "Cannot use both '--quiet' and '--verbose' options together."
        )
    level = logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


app = typer.Typer()
console = Console()


@app.command()
def summary(
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="No logging",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
):
    """Lists products short names and titles available in Aviso's catalog."""

    _setup_logging(quiet=quiet, verbose=verbose)

    catalog = ac_core.summary()
    table = Table(show_header=True, header_style="bold magenta", title="Aviso Catalog")

    table.add_column("Short Name", style="cyan")
    table.add_column("Title")

    products_sorted = sorted(catalog.products, key=lambda p: p.short_name)

    for product in products_sorted:
        table.add_row(product.short_name or "", product.title or "")

    console.print(table)


@app.command()
def details(
    product: str = typer.Argument(..., help="Product's short name"),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="No logging",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
):
    """Details a product information from Aviso's catalog.

    To get product's short name, use 'summary' command.
    """

    _setup_logging(quiet=quiet, verbose=verbose)

    try:
        product_info = ac_core.details(product)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan", width=25)
        table.add_column("Value", style="white")

        for f in fields(product_info):
            value = getattr(product_info, f.name)
            label = f.metadata.get("label", f.name)

            if isinstance(value, tuple):
                formatted = ", ".join(str(x) for x in value)
            else:
                formatted = str(value)
            table.add_row(label, formatted)

        console.print(Panel(table, title=f"[green]Product: {product}[/]", expand=False))

    except InvalidProductError:
        msg = (
            f"'{product}' doesn't exist in Aviso catalog. "
            + "Please use 'summary' command to get product's short name."
        )
        raise typer.BadParameter(msg)


def comma_separated_ints(value: str) -> list[int]:
    return sorted(
        {
            n
            for part in value.split(",")
            if part.strip()
            for n in _parse_ranges(part.strip())
        }
    )


def _parse_ranges(expr: str) -> list[int]:
    if "-" not in expr:
        return [int(expr)]
    start, end = expr.split("-")
    start, end = int(start), int(end)
    if start <= end:
        return range(start, end + 1)
    msg = f"Invalid range '{expr}': start '{start}' must be less than end '{end}'."
    raise typer.BadParameter(msg)


@app.command()
def get(
    product: str = typer.Argument(..., help="Product's short name"),
    output: Path = typer.Option(..., "--output", "-o", help="Output directory"),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        "-O",
        help="Overwrite files if they already exist",
    ),
    cycle_number: list = typer.Option(
        None,
        "--cycle",
        "-c",
        help="Cycle number(s). Comma separated values or ranges accepted.",
        parser=comma_separated_ints,
    ),
    pass_number: list = typer.Option(
        None,
        "--pass",
        "-p",
        help="Pass number(s). Comma separated values or ranges accepted.",
        parser=comma_separated_ints,
    ),
    start: str = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
    version: str = typer.Option(
        None,
        "--version",
        "-V",
        help="Product's version. By default, last version is selected",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="No logging",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
):
    """Downloads a product from Aviso's Thredds Data Server.

    Example : get a_prod_short_name --output tmp_dir
    --cycle 7,8 --pass 12-14,21 --version 1.0
    """

    _setup_logging(quiet=quiet, verbose=verbose)

    try:
        downloaded_files = ac_core.get(
            product_short_name=product,
            output_dir=output,
            cycle_number=cycle_number if cycle_number else None,
            pass_number=pass_number if pass_number else None,
            time=(start, end),
            version=version,
            overwrite=overwrite,
        )

        console.print(f"[green]Local files ({len(downloaded_files)}) :[/]")

        for file in downloaded_files:
            console.print(f"- {file}")

    except InvalidProductError:
        msg = (
            f"'{product}' doesn't exist in Aviso catalog. "
            "Please use 'summary' command to get product's short name."
        )
        raise typer.BadParameter(msg)
