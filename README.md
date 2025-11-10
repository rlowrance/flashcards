# A command-line spaced repetition flash card program

_Simplified Anki in a terminal_

I have been a heavy user of Anki, the flash card program, but found
that I mostly did not need the visual representation of flash cards
and almost always said that I had a good recall or that the card
should be presented again. Entering cards in the Anki GUI was more
time-consuming than I would prefer.

The flashcards.py program overcomes this problem by

- Using a text file to hold the cards. A text file is easy for me to
  edit, as I am proficient with at least one text editor. I use Emacs,
  but any text editor can be used.

- Running the program in the terminal. I do a lot of software
  development and many of the cards I will want to study are about
  software engineering, so running a flash card program in a terminal
  is natural for me.

- Reducing the number of options for evaluating my response to just
  two: good enough or not good enough. After Anki presents a prompt
  from a flash card, it allows you to key in your response and then
  shows it the expected response that you previously entered. You can
  rate your response as "again" (you got the card wrong), "hard" (you
  were right but had difficulty recalling the answer), "good" (you
  were right)", or "easy" (you knew the right answer
  immediately). Anki's documentation says that the most common
  evaluation is "good", so I decided that I would have only two
  evalutions: "again" (I didn't recall the response) and "good" (I did
  recall it).

I decided to make the text file an org-mode file because I use
org-mode all the time and could take advantage of org-mode's ability
to create and manage text files structured as outlines. You can ignore
the outline capability if your text editor doesn't support it (but
many do).



## Usage
1. Create a text file, say "madrid.org" containing your flash cards. A line in the file looks like this:
```
The capital of Spain is {}.\Madrid
The name "Madrid" meant {} in its original Arabic.\place of many streams
```

The format is a prompt followed by the expected response separated by a backslash character. The backslash was chosen as a field separator because it was not frequently occuring in the material I want to study with flash cards.

In addition to cards like the above, you can add comments and heading to the file. A comment is any line with a "#" it its first position. A heading is any lne with a "*" in its first position.

In my flash card files, I use a top-level heading for the name of the chapter from which the card was derived.

If I think I may need to go back to the source work, I put the page number in the source as the first few characters of the card line.

Here's an example, my first few of my cards for Richard Ovenden's "Burning the Books" (2002). These are in the file `cards-ovenden-2022.org`.
```
* Introduction
9 Keeping every document is {}.\economically unsustainable
13 In the UK, local authorities were required to provide libraries starting in {}.\1964
* Chapter 1: Crack Clay Under the Mounds
17 Xeneophone was {}.\a Greek general and historian
```

You can use any characters to indicate the omitted fill-in-the-blank material. I used "{}" because it is easy for my eyes to spot.

2. Run this command in a terminal
```
$ flashcards madrid.org
```
3. Respond to the prompts in the terminal. When all the cards have been presented, the program will overwrite the input file, which will hold the information needed to schedule spaced repetitions in the future.


## Installation

To install, clone this repo. Enter your terminal app and change to your cloned directory.

You will probably need to edit the shebang line at the top of the file `flashcards.py` so that it points to your installed Python interpretter. You can find out where your interpret is by entering `$ which python3`.

Make any edits needed to `flashcards.py`. Save it then run `$ chmod +x install-to-home-bin.sh` then `$ ./install-to-home-bin.sh`.
You will find the flashcard common in your bin directory, `~/bin`.


## Invocation

I created a directory with all my flash cards files in it. I have one file for each topic. For example, I have a file `torch.org` which holds flash cards related to the `pytorch` library.

You run the program by entering `$ flashcards torch.org` in a terminal.

The program will read `torch.org` and present to you any cards in it that are due. A card is due if it is new or if a sufficient amount of time has passed since you last successfuly responded to the prompt in the card. A successful response is one you rated "good" instead of "again."

A card will be repetetively presented until you say your recall was "good." However, any time you are prompted you can tell the program to quit by entering "q" or "quit".

When you have rated all the cards as good or have quit, the original file is rewriting with additional information--the date and time of the last presentation and the interval that program will to present the card to you again.

Initially the interval is one day. Every time you mark your recall as "good" the interval is multiplied by 2.4.

To keep cards that you entered all at once from always clustering in the repetitions, the intervals for cards are spread out though randomization.

When you invoke the program you can specify `--help` or `--version`.

In my use of the program, I will often enter a lot of cards at one sitting but don't want to review all of those cards the next time I invoke the program.
Then I invoke the program using `$ flashcards --new-card-limit 10 torch.org` so that only 10 new cards are presented.

When developing the program, I used the `--develop` invocation argument to have the program print extra debugging information.

## Limitations

The program doesn't handle graphics and has a limited range of marks for how well you recalled the information.
Those limitation make the program simple to understand and to use.

## Contributing

You can fork the code and modify it.

All the code is in one Python file.

In addition to some of the Python-included libraries, I used numpy to gain access to its randomizer.

The code has been run through `black` and `pylint` with default arguments, though I haven't corrected all the `pylint` suggestions.

The license is the MIT license.

## Possible future work


## About me

I'm a data scientist. You can find me at these places:

- LinkedIn: https://www.linkedin.com/in/roylowrance/

- Medium: medium.com/@roylowrance

- Blog: https://www.roylowrance.com

## Works Cited

Anki. "Anki Manua." https://docs.ankiweb.net/studying.html. Accessed 2025-11-10.

Overden, RIchard. _Burning the Books_. The Belknap Press of Harvard University Press. 2022.
