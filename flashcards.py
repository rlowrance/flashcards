#!/Library/Frameworks/Python.framework/Versions/3.13/bin/python3
"""Terminal-based flash card program"""

from dataclasses import dataclass
import argparse
import copy
import csv
import datetime
import enum
import functools
import heapq
import io
import os.path
import shutil
import sys
from typing import Self

import numpy as np


# Error handling
def eprint(*args, **kwargs):
    """Print on stderr"""
    print(*args, file=sys.stderr, **kwargs)


def error(*args, **kwargs):
    """Print error message on stderr and exit with non-zero return code"""
    eprint(*args, **kwargs)
    sys.exit(1)


# CSV line conversions


def csv_fields(s: str, delimiter=",") -> list[str]:
    """Parse CSV fields from a string"""
    for row in csv.reader([s], delimiter=delimiter):
        return list(map(str.strip, row))  # remove leading and trailing white space


def csv_quote(row: [str], delimiter=",") -> str:
    """Return str value quoted per CSV standards"""
    with io.StringIO() as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL, delimiter=delimiter)
        writer.writerow(row)
        result = csvfile.getvalue().strip()
        return result


def test_csv_functions():
    """unit test"""
    delimiter = "\\"
    s = "a\\bb\\ccc\\dddd"
    assert csv_fields(s, delimiter=delimiter) == ["a", "bb", "ccc", "dddd"]
    assert csv_quote(["a", "bb", "ccc", "dddd"], delimiter=delimiter) == s


# Custom types


@dataclass(order=True)
class Card:
    """A flash card"""

    headings: [str]  # context for display to user
    index: int  # input line index
    prompt: str  # user is shown this
    response: str  # user should know this
    last_presentation: None | datetime.datetime  # when card was last presented
    interval: None | datetime.timedelta  # timedelta to next presentation

    def __post_init__(self):
        """Assure both last_presentation and interval are present or missing

        Both are missing if the card has not been presented.
        """
        if self.last_presentation is None:
            assert self.interval is None
        if self.interval is None:
            assert self.last_presentation is None

    @staticmethod
    def from_str(headings: [str], index: int, s: str) -> Self:
        """Construct from a string"""
        assert isinstance(headings, list)
        assert isinstance(index, int)
        assert isinstance(s, str)
        fields = csv_fields(s, delimiter="\\")
        match len(fields):
            case 2:
                return Card(headings, index, fields[0], fields[1], None, None)
            case 4:
                return Card(
                    headings,
                    index,
                    fields[0],
                    fields[1],
                    datetime.datetime.fromisoformat(fields[2]),
                    datetime.timedelta(days=float(fields[3])),
                )
            case _:
                error(
                    "line does not have two or four fields separated by \\:"
                    f"{s}\n fields found: {fields}"
                )

    def is_new(self) -> bool:
        """A Card is new if is has never been presented"""
        return self.last_presentation is None

    def is_old(self) -> bool:
        """A Card is old if it has been presented"""
        return not self.is_new()

    def next_presentation(self) -> datetime.datetime:
        """Return next time Card should be presented"""
        return (
            datetime.datetime.now()
            if self.last_presentation is None
            else self.last_presentation + self.interval
        )

    def total_hours(self) -> float:
        """Return total number of cards in the card's interval"""
        return self.interval.total_seconds() / (24 * 60 * 60)

    def as_csv_string(self) -> str:
        """Return a string in CSV format"""
        fields = (
            [self.prompt, self.response]
            if self.is_new()
            else [self.prompt, self.response, self.last_presentation.isoformat(timespec="minutes"), str(round(self.total_hours(), 2))]
        )
        return csv_quote(fields, delimiter="\\")   
            


def test_card_from_str():
    """unit test"""
    headings = ["a", "b"]
    assert Card.from_str(headings, 123, "p\\e") == Card(
        headings, 123, "p", "e", None, None
    )
    expected_last_presentation = datetime.datetime(2025, 12, 25, hour=11, minute=3)
    expected_interval = datetime.timedelta(days=1.23)
    expected_card = Card(
        [], 456, "prompt", "expected", expected_last_presentation, expected_interval
    )
    assert (
        Card.from_str([], 456, "prompt\\expected\\20251225T1103\\1.23") == expected_card
    )


@enum.unique
class InputLineKind(enum.Enum):
    """All the types of an input line"""

    CARD = 1
    COMMENT = 2
    EMPTY = 3
    HEADING = 4


@dataclass
class InputLine:
    """Track the index into to file so that we can reconstruct the file when we write it"""

    index: int
    text: str

    def kind(self) -> InputLineKind:
        """Determine kind of the line"""
        if len(self.text) > 0 and self.text[0] == "*":
            return InputLineKind.HEADING
        if len(self.text) > 0 and self.text[0] == "#":
            return InputLineKind.COMMENT
        if len(self.text) == 0 or self.text.isspace():
            return InputLineKind.EMPTY
        return InputLineKind.CARD

    def heading_depth(self) -> int:
        """Return number of *'s at start of line"""

        def recur(remaining, result):
            if len(remaining) == 0:
                return result
            if remaining[0] != "*":
                return result
            return recur(remaining[1:], result + 1)

        return recur(self.text, 0)


class CardQueue:
    """Queue of cards ordered by their next presentation datetimes"""

    def __init__(self, cards):
        self._heap = []
        for card in cards:
            self.push(card)

    def __len__(self):
        return len(self._heap)

    def items(self) -> list:
        """Return all the Cards"""
        return self._heap

    def peek(self) -> Card:
        """Return first card without changing the queue"""
        assert len(self._heap) > 0
        popped = self.pop()
        self.push(popped)
        return popped

    def pop(self) -> Card:
        """Remove and return the first card"""
        assert len(self._heap) > 0
        first = heapq.heappop(self._heap)
        return first[1]  # [0]=key [1]=Card

    def push(self, card):
        """Mutate queue to contain a new card"""
        assert isinstance(card, Card)
        heapq.heappush(self._heap, (card.next_presentation(), card))

class InputFile:
    """Utilities for handling the input file"""
    def __init__(self, filename):
        self.filename = filename
        # Info from an input line that is a card is in self.lines (as a str) and in self.cards (parsed into fields)
        self.input_lines: [InputLine] = []   # every input line
        self.cards: [Card] = []   # some input lines contain cards, which are stored here

    def create_backup_file(self) -> None:
        """Create backup copy of file with name suffixed by current datetime"""
        # ref: Google Search Labs
        assert os.path.exists(self.filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        backup_file_name = f"{self.filename}.{timestamp}.bak"
        try:
            shutil.copy2(self.filename, backup_file_name)  # preserves some metadata
        except FileNotFoundError as e:
            error(f"error creating backup of {self.filename}: {e}")

    def read(self, new_card_limit: int | None, verbose: bool) -> None:
        """Mutate self from file creating lines and cards (a subset of lines)"""
        assert new_card_limit is None or new_card_limit >= 0
        assert os.path.isfile(self.filename)
        with open(self.filename, "r", encoding="utf-8") as file:
            raw_lines = file.readlines()

        self.input_lines = [InputLine(index, raw_line.rstrip())
                            for index, raw_line in enumerate(raw_lines)]
        self._make_cards(len(self.input_lines) if new_card_limit is None else new_card_limit, verbose)

    def _make_cards(self, n_remaining_new_cards: int, verbose: bool):
        """Mutate self by finding and appending up to n_remaining_new_cards"""
        def new_headings(heading: InputLine, current_headings: [str]) -> [str]:
            if verbose: print(f"new_headings: {heading} {current_headings}")
            depth = heading.heading_depth()
            if len(current_headings) == depth - 1:
                return current_headings + [heading.text]
            if len(current_headings) < depth - 1:
                return new_headings(heading, current_headings + [" "])
            current_headings.pop()
            return new_headings(heading, current_headings)
            
        current_headings = []
        for input_line in self.input_lines:
            if verbose:
                print(current_headings, input_line)
            if input_line.kind() == InputLineKind.HEADING:
                current_headings = new_headings(input_line, copy.deepcopy(current_headings))
                if verbose:
                    print('updated current_headings', current_headings)
            elif input_line.kind() == InputLineKind.CARD:
                # NOTE: copy the headings because they are mutated above
                card = Card.from_str(copy.deepcopy(current_headings), input_line.index, input_line.text)
                if card.is_old():
                    self.cards.append(card)
                elif card.is_new() and n_remaining_new_cards > 0:
                    self.cards.append(card)
                    n_remaining_new_cards -= 1
                

    def overwrite_original_file(self, verbose: bool) -> None:
        """Write lines and miutated cards to an output file"""
        card_for_index = {card.index: card for card in self.cards}
        with open(self.filename, "w", encoding="utf-8") as file:
            n_lines_written = 0
            for input_line in self.input_lines:  # sorted by index
                if input_line.kind() == InputLineKind.CARD and input_line.index in card_for_index:
                    s = card_for_index[input_line.index].as_csv_string()
                else:
                    s = input_line.text

                if verbose:
                    print(f"writing line: {s}")
                file.write(s + "\n")
                n_lines_written += 1
        print(f"wrote {n_lines_written} lines to file {self.filename}")
 
        

def make_parser() -> argparse.ArgumentParser:
    """Return an Argument Parse"""
    parser = argparse.ArgumentParser(
        description="terminal-based flash cards, a spaced repetition program",
        epilog="More help can be found at https://rlowrance.github.com/flashcards",
    )

    parser.add_argument("--develop", action="store_true", default=False, help="turn on additional output that may help the developer")
    parser.add_argument('--new-card-limit', action='store', default=None, type=int, help="limit number of new cards (default: present all new cards)")
    parser.add_argument("--version", action='version', version="%(prog)s 1.2")

    parser.add_argument("filename", nargs="*", help="filename to read and rewrite (required)")
    return parser


def make_uniform_random_sampler():
    """Return a function that samples from a uniform interval"""
    rnd = np.random.default_rng()  # No seed by intention

    def random_interval(mean_interval: datetime.timedelta) -> datetime.timedelta:
        """Sample and return an interval centered on the specified mean"""
        assert isinstance(mean_interval, datetime.timedelta)
        mean_seconds = mean_interval.total_seconds()
        sample = rnd.uniform(0.5 * mean_seconds, 1.5 * mean_seconds)
        return datetime.timedelta(seconds=sample)

    return random_interval


def main():
    """Run main program"""
    parser = make_parser()

    def error_print_help(*args, **kwargs):
        eprint(*args, **kwargs)
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()  # take args from sys.argv

    if args.develop:
        print("args", args)

    if args.filename is None or len(args.filename) != 1:
        error_print_help("Did not supply one filename")

    filename = args.filename[0]
    if not os.path.exists(filename):
        error_print_help(f"File does not exist: {filename}")

    input_file = InputFile(filename)
    input_file.create_backup_file()
    input_file.read(2, args.develop)  # FIXME: first arg is a testing stub
    
    if len(input_file.input_lines) == 0:
        print(f"empty input file: {args.filename}")
        sys.exit(0)
    if args.develop:
        print("lines read")
        for input_line in input_file.input_lines:
            print(f"line:  {input_line}")
        for card in input_file.cards:
            print(f"card: {card}")
    print_input_summary(input_file)
    if len(input_file.cards) == 0:
        print("No cards were found")
        sys.exit(0)

    # Spread out intervals to spread out cards introduced at the same time
    random_sampler = make_uniform_random_sampler()
    process_cards(input_file.cards, random_sampler, args.develop)  # mutate cards
    input_file.overwrite_original_file(args.develop)


def print_input_summary(input_file: InputFile) -> None:
    """Print a summary of the input lines"""
    print(f"read {len(input_file.input_lines)} lines")

    new_cards = [card for card in input_file.cards if card.is_new()]
    old_cards = [card for card in input_file.cards if card.is_old()]
    old_due_cards = [card for card in old_cards if card.next_presentation() <= datetime.datetime.now()]
    print(f"found {len(new_cards)} new cards, all of which are due")
    print(f"found {len(old_cards)} old cards, {len(old_due_cards)} of which are due ")

    if len(old_cards) > 0:
        old_card_intervals = [card.interval for card in old_cards]
        max_interval = max(old_card_intervals)
        sum_intervals = functools.reduce(
            lambda x, y: x + y, old_card_intervals, datetime.timedelta(seconds=0)
        )
        avg_interval = sum_intervals / len(old_cards)
        print(
            f"average interval for old cards is {avg_interval.days} days, {round(avg_interval.seconds/60/60, 1)} hours"
        )
        print(
            f"longest interval for old cards is {max_interval.days} days, {round(max_interval.seconds/60/60, 1)} hours"
        )


def process_card(card, verbose) -> str:
    """Present a card and return its rating or 'quit'"""
    print("")
    for heading in card.headings:
        print(heading)
    # align prompts
    p1 = f"           prompt: {card.prompt}"
    p2 = f"    your response? {' '}"
    p3 = f"expected response: {card.response}"

    print(" ")
    if verbose:
        print(f"process_card: {card}")
    print(p1)
    user_input = input(p2)
    if len(user_input) == 1 and user_input == "q":
        return "quit"
    print(p3)

    def get_rating(n_bad):
        rating = input("Rating (agq)? ")
        if rating == "a":
            return "again"
        if rating == "g":
            return "good"
        if rating == "q":
            return "quit"
        if rating == "":
            return "good"
        if n_bad > 3:
            print("assuming quit")
            return "quit"
        print("a: again")
        print("g: good")
        print("q: quit")
        print("(return): good")
        return get_rating(n_bad + 1)

    return get_rating(0)


def process_cards(cards, random_interval, verbose):
    """Present cards that are due and mutate then to reflect user choices"""
    card_queue = CardQueue(cards)  # cards are ordered by next presentation date

    prelook = datetime.timedelta(hours=1)
    days_1 = datetime.timedelta(days=1)
    while True:
        if verbose:
            print("CardQueue")
            for card in card_queue.items():
                print(card)
        card = card_queue.pop()  # retrieve card with lowest next presentation date
        if card.next_presentation() > datetime.datetime.now() + prelook:
            break
        rating = process_card(card, verbose)  # mutate card
        match rating:
            case "again":
                card.last_presentation = datetime.datetime.now()
                card.interval = datetime.timedelta(
                    minutes=10
                )  # this is within th eprelook time period
            case "good":
                if verbose:
                    print("card", card)
                    print("is_new", card.is_new())
                next_last_presentation = datetime.datetime.now()
                next_interval = random_interval(
                    days_1 if card.is_new() else max(days_1, card.interval * 2.4)
                )
                card.last_presentation = next_last_presentation
                card.interval = next_interval
            case "quit":
                return
        card_queue.push(card)

    return  # have mutated some of the cards


if __name__ == "__main__":
    main()
