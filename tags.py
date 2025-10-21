#!/Library/Frameworks/Python.framework/Versions/3.13/bin/python3
# Write report analyzing tags in one or more org-mode files

# NOTE: A previous version is at github.com/rlowrance/simple-accounting-system
# This version has substantially less code.
import argparse
import collections
import fileinput

TagUsage = collections.namedtuple('TagUsage', 'line filename lineno')

def get_arguments():
    parser = argparse.ArgumentParser(
        description='Read org-mode files, write to stdout report showing were tags were used')
    parser.add_argument(
        '--develop',
        action='store_true',
        default=False,
        help='turn on developer output')
    parser.add_argument(
        'filenames',
        nargs='*',
        help='files containing journal entries; default: stdin')
    return parser.parse_args()

def first_tag_in_line(line) -> (str, str):  # The initial : has been removed
    # A tag contains only A-z, a-z, 0-9, @, _ (NOTE: not a space)
    def recur(line, result):  # return (tag, rest_of_line)
        # print('first_tag_in_line.recur', line, result)
        if len(line) == 0: return (result, '')
        first = line[0]
        if line[0] == ':': return (result, line)
        if first == '@' or first == '_' or first.isalpha() or first.isdigit(): return recur(line[1:], result + first)
        return ('', '')
    return recur(line, '')
    
def tags_in_line(line: str) -> [str]:
    def recur(line, result):
        # print('tags_in_line.recur', line, result)
        if len(line) == 0: return result
        if line[0] == ':':
            # breakpoint()
            tag, rest = first_tag_in_line(line[1:])
            if len(tag) > 0: return recur(rest, result+[tag])
            return result
        return recur(line[1:], result)
    return recur(line, [])

def main():
    args = get_arguments()

    # process in input file, assumed to be in org-mode
    headings_for_tag = collections.defaultdict(list)
    for line in fileinput.input(args.filenames):
        if args.develop: print(f'line: {line}')
        line = line.rstrip()  # drop any final \n
        if len(line) == 0: continue
        if line[0] != '*': continue  # only process org-mode heading lines
        tags = tags_in_line(line)
        if args.develop and len(tags) > 0:
            print(f'tags in line {line} are {tags}')
            breakpoint()
        for tag in tags:
            headings_for_tag[tag].append(TagUsage(line, fileinput.filename(), fileinput.lineno()))
        if args.develop and len(headings_for_tag) > 10: break  # While developing

    # create report on stdout
    print('* headings for each tag')
    for tag in sorted(headings_for_tag.keys()):
        print(f'tag: {tag}')
        for heading in headings_for_tag[tag]:
            print(f'  {heading.line}')

    print('* all tags alphabetically')
    for tag in sorted(headings_for_tag.keys()):
        print(tag)


if __name__ == "__main__":
    main()
                    
