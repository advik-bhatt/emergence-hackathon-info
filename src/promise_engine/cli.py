"""The Promise Engine, from the terminal.

Runs entirely off the committed fixtures — no credentials required. Prints, in order: the
falsification preamble, the ops work-queue, the Rio callout, and the agent's narrative.

    uv run python -m promise_engine.cli
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from promise_engine.agent.loop import run_investigation
from promise_engine.craft.cassette import Cassette

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

VERDICT_STYLE = {"FIX": "bold red", "PAD": "yellow", "OK": "dim green"}


STEP_KIND_STYLE = {
    "probe": "cyan",
    "trap": "bold red",
    "refusal": "bold yellow",
    "resolution": "bold green",
}


def _print_preamble(console: Console, hypotheses) -> None:
    console.rule("[bold]Falsification preamble[/bold]")
    for h in hypotheses:
        if h["status"] == "DEAD":
            claim = Text(f'"{h["claim"]}"', style="dim strike")
            status = Text(" DEAD", style="dim")
        else:
            claim = Text(f'"{h["claim"]}"', style="bold green")
            status = Text(" SURVIVES", style="bold green")
        console.print(claim, status)
        console.print(Text(f"  {h['evidence']}", style="dim"))
        console.print()


def _print_trap(console: Console, trap: dict) -> None:
    console.rule("[bold]The Trap[/bold]")
    console.print(
        "[dim]If reviews are the only outcome this dataset can measure, what promise "
        "maximizes them?[/dim]"
    )
    console.print()

    curve_by_day = {point["extra_days"]: point for point in trap["curve"]}
    sample_days = [0, 5, 10, 15, 20, 30]

    table = Table(show_header=True, header_style="bold", pad_edge=False, padding=(0, 1))
    table.add_column("Extra promise (D days)", justify="right", no_wrap=True)
    table.add_column("Avg review", justify="right", no_wrap=True)
    table.add_column("1-star %", justify="right", no_wrap=True)
    table.add_column("Late %", justify="right", no_wrap=True)
    for day in sample_days:
        point = curve_by_day.get(day)
        if point is None:
            continue
        table.add_row(
            f"+{day}",
            f"{point['avg_review']:.2f}",
            f"{point['one_star_rate'] * 100:.1f}%",
            f"{point['late_rate'] * 100:.1f}%",
        )
    console.print(table)
    console.print(
        "[dim]Climbing, then flat: every additional day is free, and the data never says "
        "stop.[/dim]"
    )
    console.print()

    console.print(Text("UNBOUNDED", style="bold red on default"), Text(" — the review-"
        "maximizing promise is +infinity.", style="bold red"))
    console.print()
    console.print(Panel(trap["why_we_refuse"], title="[bold]Why we refuse it[/bold]",
                         border_style="yellow"))
    console.print(f"[dim]{trap['caveat']}[/dim]")
    console.print()


def _print_trace(console: Console, steps) -> None:
    console.rule("[bold]Reasoning trace[/bold]")
    for i, step in enumerate(steps, start=1):
        style = STEP_KIND_STYLE.get(step["kind"], "")
        tag = Text(f" {step['kind'].upper()} ", style=f"bold reverse {style}".strip())
        console.print(f"[dim]{i}.[/dim]", tag, Text(f" {step['tool']}", style="dim"))
        console.print(f"   {step['finding']}")
    console.print()


def _print_queue(console: Console, lanes) -> None:
    console.rule("[bold]Ops work queue[/bold] (ranked by orders at risk)")
    # Headers are terse and every column is no_wrap: "orders at risk" is the headline
    # number of this table, and a demo that renders it as "135,8…" has buried the finding.
    table = Table(show_header=True, header_style="bold", pad_edge=False, padding=(0, 1))
    table.add_column("State", no_wrap=True)
    table.add_column("Orders", justify="right", no_wrap=True)
    table.add_column("Promise", justify="right", no_wrap=True)
    table.add_column("Med", justify="right", no_wrap=True)
    table.add_column("p95", justify="right", no_wrap=True)
    table.add_column("Gap", justify="right", no_wrap=True)
    table.add_column("Late", justify="right", no_wrap=True)
    table.add_column("At risk", justify="right", no_wrap=True)
    table.add_column("Verdict", no_wrap=True)

    for lane in lanes:
        style = VERDICT_STYLE.get(lane["verdict"], "")
        verdict_text = Text(lane["verdict"], style=style)
        if lane["is_borderline"]:
            verdict_text.append(" ~", style="italic yellow")
        table.add_row(
            lane["state"],
            f"{lane['orders']:,}",
            f"{lane['current_promise']:.1f}",
            f"{lane['median_days']:.0f}",
            f"{lane['p95_days']:.1f}",
            f"{lane['gap']:+.1f}",
            f"{lane['late_rate']:.1f}%",
            f"{lane['orders_at_risk']:,.0f}",
            verdict_text,
        )
    console.print(table)
    console.print("[dim]~ = borderline: the verdict flips on a sub-day change in p95.[/dim]")
    console.print()


def _print_rio_callout(console: Console, lanes) -> None:
    rio = next((lane for lane in lanes if lane["state"] == "RJ"), None)
    if rio is None:
        return
    body = (
        f"[bold]Median[/bold] {rio['median_days']:.0f} days   "
        f"[bold]p95[/bold] {rio['p95_days']:.0f} days   "
        f"[bold]Promised[/bold] {rio['current_promise']:.0f} days   "
        f"→ [bold red]{rio['verdict']}[/bold red]\n\n"
        f"Rio de Janeiro isn't slow — half its deliveries land in "
        f"{rio['median_days']:.0f} days. It's unpredictable: 1 in 7 customers "
        f"({rio['late_rate']:.1f}%) wait as long as {rio['p95_days']:.0f} days. Olist's #2 "
        f"market, right next to São Paulo, and the estimator fails exactly where the tail is "
        f"fat. Padding the promise to {rio['p95_days']:.0f} days would keep the letter of the "
        f"word while making Rio look like a remote outpost. This verdict is robust — it would "
        f"take {rio['flip_distance']:.1f} days of p95 movement to flip it."
    )
    console.print(Panel(body, title="[bold]Rio de Janeiro[/bold]", border_style="red"))
    console.print()


def main() -> None:
    console = Console()
    cassette = Cassette(FIXTURES_DIR)
    investigation = run_investigation(cassette)

    _print_preamble(console, investigation.hypotheses)
    _print_trap(console, investigation.trap)
    _print_trace(console, [
        {"tool": s.tool, "kind": s.kind, "finding": s.finding} for s in investigation.steps
    ])
    _print_queue(console, investigation.lanes)
    _print_rio_callout(console, investigation.lanes)

    console.rule("[bold]The agent's narrative[/bold]")
    console.print(investigation.narrative)
    console.print()


if __name__ == "__main__":
    main()
