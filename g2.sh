cp /Users/roylowrance/Dropbox/3-areas/flash-cards/my-cards.org my-cards.org
cp my-cards.org my-cards-original.org
python3 flashcards.py --develop my-cards.org
diff my-cards.org my-cards-original.org

