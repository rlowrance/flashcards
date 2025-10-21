# Analyze Tags in Org-mode Files

## Usage

This Python command-line program reads one or more Emacs Org-mode
files and prints a report on stdout saying which headlines mention
which tags.

The printed file is formatted as an Org-mode file. Typically I pipe it
to a temporary file which I open in Emacs.

My main use case for the command is around a large Org-mode file I
maintain. That file has most of my notes in it--it's a "one big text
file" (OBTF).  Each note begins with an Org-mode header, which is a line starting with a "*". Some of the headers
have Org-mode tags in them. In Org-mode, a tag is sequence of
characters written between colons, as in `:tag:` (which is one tag)
and `:tag1:tag2:` which are two tags. Org-mode expects tags to
contains only alphabetic or numeric characters or the characters "@"
or "_". My tags mostly reflect the topics in the note.

I use this command to find misspelled tags. That works because the
command prints tags in alphabetic order.

I also use it to find all the notes on a given topic. I use this when
assembling research for a writing project or deciding on futher
research.

## Installation

To install, clone this repo then copy the file `tags.py` to a
directory that is in your path. If you use your `~/bin` directory, you
can do this by running the script `install-into-home-bin.sh` and setting
your `$PATH` in your shell's initialization script.

You will probably need to edit the shebang line at the top of the
script to locate your Python interpretter. In MacOS, you can run the
command `$which python3` to locate your Python command.

## Invocation

To use the command, invoke the command with one or more filenames on the command line.

Here are some examples of invocations:

- To analyze the tags in the file `journal.org`, enter `$tags
  journal.org`. Because I typically pipe the output, I enter `$tags
  journal.org > tmp.org` then open the `tmp.org` file in Emacs.

- To analyze the tags in all Org-mode files in a directory, change to
  that directory then enter `$tags *.org`. You might want to do this
  if you maintain a directory containing many of your notes.

- To analyze the tags from stdin, enter `$tags`.

The command reads the files specified, then prints to stdout a report
showing each tag and for each tag, the headlines in the file that
mention that tag.

These are the invocation options:
- `--develop` turns on additional output that I found useful as I wrote the program.
- `-h` and `--help` write help text to stdout.

## Limitations

The printed report doesn't include the file name as that would be additional clutter in the output and I use the command mostly for one file at a time.

## Contributing

The code uses these built-in Python modules:
- `argparse` to read the invocation arguments
- `collections` to create a `namedtuple` internal data type `TagUsage`.
- `fileinput` to read the input files specified on the command line or to read stdin, if no files are specified on the command line.

I don't follow typical guidelines for formatting Python source code, but you
are welcome to reformat the code using your favorite style.

The license is the MIT license.

## Possible future work

- Update the script to include the input file names in the printed
  report. Then the command would be more useful for analyzing the tags
  across multiple files.

- Extend the kinds of file analyzed to include markdown files. These
  have a tag syntax different from that used in Org-mode files.

- Build a companion capability, possibly in the same script, to
  analyze tags in file names. That requires deciding on a convention
  for putting tags in file names. I use ` -- {tag} {tag}...` to embed
  tags in file names.

- Convert the command to an Emacs function that runs inside of
  Emacs. It would run on the current buffer and create a new buffer
  with the analysis report.

## About me

I'm a data scientist. You can find me at these places:

- LinkedIn: https://www.linkedin.com/in/roylowrance/

- Medium: medium.com/@roylowrance

- Blog: https://www.roylowrance.com
