"""ONYX unified command line interface."""

import asyncio
import os
from pathlib import Path
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from onyx.config import load_config
from onyx.core.orchestrator import OnyxCore
from onyx.models.detector import detect_hardware
from onyx.models.benchmark import benchmark_model
from onyx.memory.categories import MemoryCategory
from onyx.sync.bundle import SyncBundleManager

console = Console()


@click.group()
def cli():
    """ONYX — Portable, Self-Improving Personal AI Intelligence System."""
    pass


@cli.command()
@click.option("--data-dir", default=None, help="Custom data directory")
def setup(data_dir):
    """Bootstrap ONYX directories, database, and hardware configuration."""
    console.print(Panel.fit("[bold cyan]ONYX Environment Setup[/bold cyan]", border_style="cyan"))

    config = load_config()
    if data_dir:
        config.execution.sandbox_root = str(Path(data_dir) / "workspaces")
        config.memory.sqlite_path = str(Path(data_dir) / "memory" / "onyx_memory.db")

    with console.status("[bold green]Creating directories and initializing storage..."):
        config.ensure_directories()
        core = OnyxCore(config=config)
        asyncio.run(core.initialize())

    hw = detect_hardware()
    console.print(f"[green]✓[/green] Storage initialized at: [bold]{config.memory.sqlite_path}[/bold]")
    console.print(f"[green]✓[/green] Sandboxed workspaces at: [bold]{config.execution.sandbox_root}[/bold]")
    console.print(f"[green]✓[/green] Detected Hardware: [bold]{hw.os_name} {hw.architecture}[/bold] ({hw.cpu_cores} cores, {hw.ram_gb} GB RAM)")
    if hw.has_mps:
        console.print("[green]✓[/green] Apple Metal (MPS) acceleration: [bold]Available[/bold]")
    if hw.has_cuda:
        console.print(f"[green]✓[/green] NVIDIA CUDA acceleration: [bold]{hw.cuda_device_name} ({hw.cuda_vram_gb} GB)[/bold]")

    console.print("\n[bold green]ONYX setup complete![/bold green] Run [cyan]onyx start[/cyan] to launch.")


@cli.command()
@click.option("--host", default=None, help="Host address to bind")
@click.option("--port", default=None, type=int, help="Port to listen on")
def start(host, port):
    """Start the ONYX core runtime and web console."""
    import uvicorn
    from onyx.api.server import create_app

    config = load_config()
    bind_host = host or config.server.host
    bind_port = port or config.server.port

    console.print(Panel.fit(
        f"[bold cyan]ONYX Intelligence System v0.2.0[/bold cyan]\n"
        f"Local Console: [bold green]http://{bind_host}:{bind_port}[/bold green]\n"
        f"API Gateway:   [bold]http://{bind_host}:{bind_port}/api/v1[/bold]\n"
        f"Active Node:   [bold]{config.sync.node_id}[/bold]",
        border_style="cyan"
    ))

    app = create_app(config=config)
    uvicorn.run(app, host=bind_host, port=bind_port, log_level="info")


@cli.command()
def doctor():
    """Run comprehensive system and hardware diagnostics."""
    console.print("[bold cyan]ONYX System Doctor Diagnostics[/bold cyan]\n")
    hw = detect_hardware()

    table = Table(title="Hardware & Runtime Environment")
    table.add_column("Property", style="cyan")
    table.add_column("Detected Value", style="green")

    table.add_row("Operating System", f"{hw.os_name} ({hw.architecture})")
    table.add_row("CPU Cores", str(hw.cpu_cores))
    table.add_row("System RAM", f"{hw.ram_gb} GB")
    table.add_row("Disk Free", f"{hw.disk_free_gb} GB")
    table.add_row("Apple Silicon", str(hw.apple_silicon))
    table.add_row("Metal (MPS)", "Supported" if hw.has_mps else "Not detected")
    table.add_row("CUDA Acceleration", f"{hw.cuda_device_name} ({hw.cuda_vram_gb} GB)" if hw.has_cuda else "None")
    table.add_row("Recommended Quantization", hw.recommended_quantization)
    table.add_row("Recommended Model Backend", hw.recommended_backend)
    table.add_row("Python Runtime", sys.version.split()[0])

    console.print(table)


@cli.command()
def chat():
    """Start an interactive terminal chat session with ONYX."""
    core = OnyxCore()
    asyncio.run(core.initialize())

    console.print(Panel.fit(
        f"[bold cyan]ONYX Interactive Terminal Session[/bold cyan]\n"
        f"Owner: [bold]{core.identity.owner}[/bold] | Model: [bold]{core.model_registry.active_adapter_name}[/bold]\n"
        f"Type [yellow]exit[/yellow] or [yellow]quit[/yellow] to end session.",
        border_style="cyan"
    ))

    while True:
        try:
            user_input = console.input("[bold green]You > [/bold green]").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[cyan]ONYX session ended.[/cyan]")
                break

            with console.status("[bold cyan]ONYX is thinking..."):
                response = asyncio.run(core.process_message(user_input))

            console.print(f"[bold cyan]ONYX > [/bold cyan]{response}\n")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[cyan]Session closed.[/cyan]")
            break


@cli.group()
def memory():
    """Inspect and manage personal memory."""
    pass


@memory.command("list")
@click.option("--limit", default=20, help="Maximum records to show")
def memory_list(limit):
    """List recent memory records."""
    core = OnyxCore()
    asyncio.run(core.initialize())
    records = asyncio.run(core.memory.store.export_all())

    table = Table(title="Personal Memory Records")
    table.add_column("Category", style="cyan")
    table.add_column("Content", style="white")
    table.add_column("Source", style="dim")

    for r in records[-limit:]:
        table.add_row(r.category.value, r.content[:80] + ("..." if len(r.content) > 80 else ""), r.source)

    console.print(table)


@memory.command("search")
@click.argument("query")
def memory_search(query):
    """Search personal memory by semantic similarity."""
    core = OnyxCore()
    asyncio.run(core.initialize())
    results = asyncio.run(core.memory.recall(query=query, limit=5))

    console.print(f"[bold cyan]Semantic Search Results for:[/bold cyan] '{query}'\n")
    for r, score in results:
        console.print(f"- [green][{score:.2f}][/green] [{r.category.value}] {r.content}")


@memory.command("backup")
@click.argument("output_path")
def memory_backup(output_path):
    """Export memory snapshot to a backup file."""
    core = OnyxCore()
    asyncio.run(core.initialize())
    path = asyncio.run(core.memory.backup(output_path))
    console.print(f"[green]✓[/green] Memory backup successfully exported to: [bold]{path}[/bold]")


@memory.command("restore")
@click.argument("input_path")
def memory_restore(input_path):
    """Restore memory from a backup file."""
    core = OnyxCore()
    asyncio.run(core.initialize())
    count = asyncio.run(core.memory.restore(input_path))
    console.print(f"[green]✓[/green] Restored [bold]{count}[/bold] records from {input_path}")


@cli.group()
def obsidian():
    """Obsidian vault note and connection synchronization."""
    pass


@obsidian.command("sync")
@click.option("--vault-path", default=None, help="Path to your Obsidian vault directory")
def obsidian_sync(vault_path):
    """Index markdown notes, tags, wikilinks, and connections into ONYX memory."""
    from onyx.memory.obsidian import ObsidianSyncEngine
    config = load_config()
    target_path = vault_path or config.memory.obsidian_vault_path
    
    core = OnyxCore(config=config)
    asyncio.run(core.initialize())
    engine = ObsidianSyncEngine(memory=core.memory)
    
    with console.status(f"[bold cyan]Scanning and synchronizing Obsidian vault at {target_path}..."):
        res = asyncio.run(engine.sync_vault(target_path))
        
    console.print(f"[green]✓[/green] Obsidian vault synchronized: [bold]{res['vault_path']}[/bold]")
    console.print(f"    Notes Indexed: [bold cyan]{res['notes_indexed']}[/bold cyan]")
    console.print(f"    Connections Found: [bold magenta]{res['connections_found']}[/bold magenta]")
    console.print(f"    Categories Updated: {', '.join(res['categories'])}")


@cli.group()
def sync():
    """Node synchronization and portable bundle export/import."""
    pass


@sync.command("export")
@click.option("--name", default=None, help="Custom bundle file name")
def sync_export(name):
    """Export approved memories into a signed sync bundle (.onyx)."""
    core = OnyxCore()
    asyncio.run(core.initialize())
    mgr = SyncBundleManager()
    bundle = asyncio.run(mgr.export_bundle(core.memory, bundle_name=name))
    console.print(f"[green]✓[/green] Sync bundle created: [bold]{bundle}[/bold]")


@sync.command("import")
@click.argument("bundle_path")
def sync_import(bundle_path):
    """Import and verify an ONYX sync bundle (.onyx)."""
    core = OnyxCore()
    asyncio.run(core.initialize())
    mgr = SyncBundleManager()
    res = asyncio.run(mgr.import_bundle(bundle_path, core.memory))
    console.print(f"[green]✓[/green] Successfully verified and imported bundle from node [bold]{res['source_node']}[/bold]")
    console.print(f"    New records: {res['new_imported']}, Updated conflicts: {res['updated_conflicts']}")


@cli.command()
def benchmark():
    """Run model inference benchmark."""
    core = OnyxCore()
    asyncio.run(core.initialize())
    adapter = asyncio.run(core.model_registry.get_or_fallback())

    with console.status(f"[bold cyan]Benchmarking {adapter.model_name}..."):
        res = asyncio.run(benchmark_model(adapter))

    table = Table(title=f"Inference Benchmark: {res.model_name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("TTFT (Time to first token)", f"{res.ttft_seconds} s")
    table.add_row("Total Time", f"{res.total_seconds} s")
    table.add_row("Throughput", f"{res.tokens_per_second} tokens/sec")
    table.add_row("Tokens Generated", str(res.completion_tokens))
    console.print(table)


def main():
    cli()


if __name__ == "__main__":
    main()
