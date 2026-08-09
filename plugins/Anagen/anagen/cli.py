"""Click CLI for anagen."""

import click

from .dictionary import (
    DEFAULT_DICTIONARY,
    build_specialized_dictionary,
    get_cache_dir,
    load_specialized_dictionary,
)
from .generator import build_pos_buckets, generate_anagrams
from .letters import letter_counter


class AnagenGroup(click.Group):
    """Lets ``anagen SOME TEXT`` implicitly mean ``anagen generate SOME TEXT``.

    Click's group parses its own options before subcommand dispatch, so
    the default-command rewrite has to happen in parse_args (before that
    parsing runs) rather than in resolve_command (which runs after).
    """

    def parse_args(self, ctx, args):
        if args and args[0] not in self.commands and args[0] not in ("-h", "--help", "--version"):
            args = ["generate", *args]
        return super().parse_args(ctx, args)


@click.group(cls=AnagenGroup)
@click.version_option()
def cli():
    """anagen - generate grammatically plausible English anagrams.

    Run ``anagen SOME TEXT`` to generate anagrams directly, or
    ``anagen init`` to (re)build the specialized dictionary first.
    """


@cli.command()
@click.argument("text", nargs=-1, required=True)
@click.option(
    "-n", "--number", default=1, show_default=True, type=click.IntRange(min=1),
    help="Number of unique anagrams to attempt to generate.",
)
@click.option(
    "-d", "--dictionary", "dictionary_path", default=DEFAULT_DICTIONARY, show_default=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Word list used as the base source of valid words.",
)
@click.option(
    "--max-words", default=6, show_default=True, type=click.IntRange(min=1),
    help="Maximum number of words per generated anagram.",
)
@click.option(
    "--time-budget", default=8.0, show_default=True, type=float,
    help="Maximum seconds to search before giving up.",
)
def generate(text, number, dictionary_path, max_words, time_budget):
    """Generate anagrams of TEXT that follow simple English grammar rules."""
    phrase = " ".join(text)
    counts = letter_counter(phrase)
    if not counts:
        raise click.ClickException("Input text contains no letters to anagram.")

    cache_dir = get_cache_dir()
    pos_map = load_specialized_dictionary(dictionary_path, cache_dir)
    if pos_map is None:
        click.echo(
            "No specialized dictionary cached yet; building one now "
            "(run 'anagen init' ahead of time to avoid this delay)...",
            err=True,
        )
        pos_map = build_specialized_dictionary(dictionary_path, cache_dir)

    buckets = build_pos_buckets(pos_map)
    results = generate_anagrams(
        counts, buckets, number=number, max_words=max_words, time_budget=time_budget
    )

    if not results:
        raise click.ClickException(
            "No grammatical anagram found for the given text within the search budget."
        )

    for sentence in results:
        click.echo(sentence)

    if len(results) < number:
        click.echo(f"(only found {len(results)} of {number} requested)", err=True)


@cli.command()
@click.option(
    "-d", "--dictionary", "dictionary_path", default=DEFAULT_DICTIONARY, show_default=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Base word list to specialize with part-of-speech tags.",
)
@click.option("--force", is_flag=True, help="Rebuild even if a cached dictionary already exists.")
def init(dictionary_path, force):
    """Build the specialized, part-of-speech-tagged dictionary anagen needs.

    /usr/share/dict/words and similar wordlists are flat -- they don't
    say which words are nouns, verbs, adjectives, etc. This command
    cross-references the wordlist against WordNet (downloading it via
    NLTK on first use) to tag each word, and caches the result so
    later runs of ``anagen`` don't need to rebuild it.
    """
    cache_dir = get_cache_dir()
    if not force:
        existing = load_specialized_dictionary(dictionary_path, cache_dir)
        if existing is not None:
            click.echo(
                f"Specialized dictionary already cached ({len(existing)} words). "
                "Use --force to rebuild."
            )
            return

    click.echo("Building specialized dictionary (downloading WordNet data if needed)...")
    pos_map = build_specialized_dictionary(dictionary_path, cache_dir, force=True)
    click.echo(f"Done. Tagged {len(pos_map)} words, cached in {cache_dir}")


def main():
    cli()
