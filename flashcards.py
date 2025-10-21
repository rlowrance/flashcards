# main program for tanki package
import argparse
import collections
import copy
import csv
import datetime
import heapq
import io
import os.path
import random
import shutil
import sys

from typing import Any

from . import __about__

__version__ = __about__.__version__

# Custom types
Line = collections.namedtuple('Line',
                              'index text prompt response last_presentation interval')
def line_zero() -> Line: return Line(0, '', None, None, None, None)
def line_from_fields(index, text, fields) -> Line:
    if len(fields) == 2:
        return line_from_text(index, text)._replace(
            prompt=fields[0],
            response=fields[1]
        )
    if len(fields) == 4:
        return line_from_fields(index, text, fields[0:2])._replace(
            last_presentation=make_datetime_from_str(fields[2]),
            interval=make_timedelta_from_str(fields[3])
        )
    raise ValueError(f'number of fields: {len(fields)}; field: {fields}')
def line_from_text(index, text) -> Line:
    return line_zero()._replace(
        index=index,
        text=text,
    )
def line_interval_days(line) -> float:
    return line.interval.total_seconds() / (24*60*60)
def line_kind(line) -> str:
    if line.prompt is None: return 'text'
    if line.last_presentation is None: return 'newcard'
    return 'oldcard'
def line_next_presentation(line) -> datetime.datetime:
    kind = line_kind(line)
    if kind == 'text': return datetime.datetime.now()
    if kind == 'newcard': return datetime.datetime.now()
    if kind == 'oldcard': return line.last_presentation + line.interval
    raise TypeError(f'kind')
def line_short_str(line):
    kind = line_kind(line)
    if kind == 'text': return f'Line (text) {line.text}'
    if kind == 'newcard': return f'Line  (new) {line.prompt}'
    return f'Line  (old) {line.prompt} {line.last_presentation}'
def line_update_from_rating(line, rating):
    assert rating in {'again', 'good'}
    kind = line_kind(line)
    assert kind in {'newcard', 'oldcard'}
    raw_interval = (
        datetime.timedelta(minutes=10) if rating == 'again' else
        datetime.timedelta(days=1) if kind == 'newcard' else
        max(datetime.timedelta(days=1), line.interval * 2.4)
    )
    return line._replace(
        last_presentation=datetime.datetime.now(),
        interval=random.uniform(raw_interval * 0.8, raw_interval * 1.2)  # add fuzz
    )

OrderedQueue = collections.namedtuple('OrderedQueue', 'heap index')
# ref: https://www.google.com/search?client=safari&rls=en&q=python+maintain+an+ordered+queue&ie=UTF-8&oe=UTF-8
def orderedqueue_empty(): return OrderedQueue([], 0)
def orderedqueue_print(ordered_queue) -> None:
    orderedqueue_for_each(ordered_queue, lambda x: print('{x}'))
def orderedqueue_for_each(ordered_queue, f):
    q = copy.deepcopy(ordered_queue)
    while not orderedqueue_is_empty(q):
        q, item = orderedqueue_pop(q)
        f(item)
def orderedqueue_is_empty(ordered_queue) -> bool: return not ordered_queue.heap
def orderedqueue_peek(ordered_queue) -> Any:
    if orderedqueue_is_empty(ordered_queue): raise IndexError('peek from empty OrderedQueue')
    return ordered_queue.heap[0][2]  # return the item
def orderedqueue_pop(ordered_queue) -> tuple[OrderedQueue, Any]:
    if orderedqueue_is_empty(ordered_queue): raise IndexError('pop from empty OrderedQueue')
    items = heapq.heappop(ordered_queue.heap)
    return (OrderedQueue(ordered_queue.heap, ordered_queue.index), items[2])
def orderedqueue_push(ordered_queue, item, priority) -> OrderedQueue:
    heapq.heappush(ordered_queue.heap, (priority, ordered_queue.index, item))
    return OrderedQueue(ordered_queue.heap, ordered_queue.index+1)

verbose = True
def vp(*args, **kwargs):  # verbose print
    if verbose: print(*args, **kwargs)

def create_backup_file(source_file_name: str) -> None:
    # Create backup copy of file, appending current datetime
    # ref: Goofle Search Labs
    if not os.path.exists(source_file_name):
        error(f'file does not exist: {source_file_name}')
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_file_name = f'{source_file_name}.{timestamp}.bak'
    try:
        shutil.copy2(source_file_name, backup_file_name)  # preserves some metadata
    except Exception as e:
        error(f'error creating backup of {source_file_name}: {e}')

csv_delimiter = '\\'  # a single back slash

def csv_fields(s: str, delimiter=csv_delimiter) -> list[str]:
    # parse CSV fields from a string
    for row in csv.reader([s], delimiter=delimiter):
        return list(map(str.strip, row))  # remove leading and trailing white space
    
def csv_quote(s: str, delimiter=csv_delimiter) -> str:
    # return str value quoted per CSV standards
    with io.StringIO() as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL, delimiter=csv_delimiter)
        writer.writerow([s])
        result = csvfile.getvalue().strip()
        return result

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

def error(*args, **kwargs):
    eprint(*args, **kwargs)
    sys.exit(1)

def file_lines_read(filename: str) -> list[Line]:
    if not os.path.isfile(filename):
        error(f'the card file {filename} is not present')
    with open(filename, 'r') as file:
        line_index = 0
        csv_delimiter = '\\'  # a single backslash in the file
        result = []
        for line_str in file:  # retains ending new lines
            line = line_str.rstrip()
            if len(line) == 0 or line[0] == '#' or line[0] == '*' or line.isspace():
                result.append(line_from_text(
                    line_index, 
                    line))
            else:
                result.append(line_from_fields(
                    line_index, 
                    line,
                    csv_fields(line, csv_delimiter)))
            line_index += 1
    return result
            
def file_lines_write(lines: list[Line], filename: str, args) -> None:
    with open(filename, 'w') as file:
        def maybe_write(line):
            if args.debug: print(f'would write {line}')
            else: file.write(line + '\n')
        seconds_per_day = 24 * 60 * 60
        n_lines_written = 0
        for line in sorted(lines):
            kind = line_kind(line)
            if kind == 'text':
                maybe_write(line.text)
            elif kind == 'newcard':
                prompt = csv_quote(line.prompt)
                response = csv_quote(line.response)
                maybe_write(prompt + '\\' + response)
            else: 
                assert kind == 'oldcard'
                prompt = csv_quote(line.prompt)
                response = csv_quote(line.response)
                last_presentation = line.last_presentation.isoformat(timespec='minutes')
                total_seconds = line.interval.total_seconds()
                total_days = round(total_seconds/(24*60*60), 6)
                interval = f'{total_days:.6f}'
                maybe_write(prompt + '\\' + response + '\\' + last_presentation + '\\' + interval)
            n_lines_written += 1
    print(f'wrote {n_lines_written} lines to file {filename}')

def make_datetime_from_str(s: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(s)

def make_parser():
    parser = argparse.ArgumentParser(
        description='terminal-based anki, a spaced repetition program',
        epilog='More help can be found at https://rlowrance.github.com/tanki'
    )
    def add_flag(*names, **kwargs):
        parser.add_argument(*names, action='store_true', default=False, **kwargs)
    add_flag('--version', help='show version and exit')
    add_flag('--debug',help='for the developer only')
    parser.add_argument('filename', nargs='?', help='filename to read (required)')
    return parser

def make_timedelta_from_str(s: str) -> datetime.datetime:
    return datetime.timedelta(days=float(s))

def main():
    parser = make_parser()
    args = parser.parse_args()  # take args from sys.argv
    global verbose
    verbose = args.debug
    vp('args', args)
    random.seed(123)

    if args.version: 
        invocated = os.path.basename(sys.argv[0])
        print(f'{invocated} {__version__}')
        sys.exit(0)

    if args.filename is None:
        eprint('Missing required filename')
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.filename):
        eprint(f'file does not exist: {args.filename}')
        parser.print_help()
        sys.exit(1)

    create_backup_file(args.filename)

    lines: list[Line] = file_lines_read(args.filename)
    if len(lines) == 0:
        print(f'empty input file: {args.filename}')
        sys.exit(0)
    if args.debug:
        print('lines read')
        for line in lines: print(f'  {line}')
    print_lines_summary(lines)
    updated_lines = process_lines(lines, args)  # was process_cards
    file_lines_write(updated_lines, args.filename, args)  # was file_cards_write

def present_card(card) -> str:
    # present a card and return its rating or 'quit'
    print(f'{card.prompt}')
    user_input = input(f'? ')
    if len(user_input) > 0 and user_input[0] == 'q': return 'quit'
    print(f': {card.response}')  # expected response

    def get_rating(n_bad):
        rating = input('Rating (agq)? ')
        if rating == 'a': return 'again'
        if rating == 'g': return 'good'
        if rating == 'q': return 'quit'
        if rating == '': return 'good'
        if n_bad > 3:
            print('assuming quit')
            return 'quit'
        print('a: again')
        print('g: good')
        print('q: quit')
        print('(return): good')
        return get_rating(n_bad + 1)
    
    return get_rating(0)

def print_lines_summary(lines: list[Line]) -> None:
    print(f'read {len(lines)} lines; found')
    n_text_lines = 0
    n_new_cards = 0
    n_old_cards = 0
    old_cards_total_interval = datetime.timedelta(seconds=0)
    count_of_cards_on_date = collections.defaultdict(int)
    for line in lines:
        kind = line_kind(line)
        if kind == 'text': n_text_lines += 1
        if kind == 'newcard': 
            n_new_cards += 1
            date = line_next_presentation(line).date()
            count_of_cards_on_date[date] += 1
        if kind == 'oldcard': 
            n_old_cards +=1
            old_cards_total_interval += line.interval
            date = line_next_presentation(line).date()
            count_of_cards_on_date[date] += 1
    print(f' {n_text_lines} text lines')
    print(f' {n_new_cards} new cards')
    print(f' {n_old_cards} old cards')

    if n_old_cards > 0:
        mean_seconds = old_cards_total_interval.total_seconds() / n_old_cards
        mean_days = mean_seconds / (24 * 60 * 60)
        print(f'For the old card, the mean interval is {round(mean_days, 1)} days')

    print(f'The number of cards due to be presented on each date is')
    for date in sorted(count_of_cards_on_date.keys()):
        count = count_of_cards_on_date[date]
        print(f' {date}: {count}')

def process_lines(lines: list[Line], args) -> list[Line]:
    # present lines that are cards until all ready cards have been rated good
    # return possibly mutated lines
    def display(line: Line) -> str:
        kind = line_kind(line)
        result = f'  {kind}'
        if kind == 'text': 
            print(result + f' {line.text}')
            return
        print(result + f' {line_next_presentation(line)} {line.prompt}')
    
    queue = orderedqueue_empty()
    for line in lines:
        queue = orderedqueue_push(queue, 
                                  line, 
                                  line_next_presentation(line))
        
    result = []
    while not orderedqueue_is_empty(queue):
        if args.debug: 
            print('queue')
            orderedqueue_for_each(queue, display)
        queue, line = orderedqueue_pop(queue)
        if line_kind(line) == 'text':
            result.append(line)
            continue
        # present cards that are due within the hour
        next_presentation = line_next_presentation(line)
        if next_presentation > datetime.datetime.now() + datetime.timedelta(hours=1):
                result.append(line)
                continue
        rating = present_card(line)
        if rating == 'quit':
            result.append(line)
            while not orderedqueue_is_empty(queue):
                queue, line = orderedqueue_pop(queue)
                result.append(line)
            return result
        updated_line = line_update_from_rating(line, rating)
        queue = orderedqueue_push(queue, 
                                    updated_line, 
                                    line_next_presentation(updated_line))
    return result




if __name__ == '__main__':
    main()
        



                    
