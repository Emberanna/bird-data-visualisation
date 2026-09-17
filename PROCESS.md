# Process

<!-- Same as assignment 1, same honesty. Which tools you used and for what; one
thing you kept and why it was good; one thing you rejected and why it was wrong.
"I did not use any" is fine if it is true.

If a model wrote most of plot.py, which is likely and allowed, the interesting part
is what you had to correct: did it invent a column name, use pandas where a list
would do, silently drop the rows it could not parse? -->

## Tools

I used ChatGPT to help me understand the assignment instructions, find a suitable GBIF data source, and write and revise the Python code for fetching and plotting the data. I used VS Code to edit and run the scripts, and GitHub to store the repository and check the submitted files.

## Kept

I kept the suggestion to count the scientific names in the GBIF occurrence records and show the ten most frequent species as a horizontal bar chart. This worked well because the JSON data contains scientific names, and the bar chart makes the differences in record counts easy to compare.

## Rejected

I rejected the original template's Hong Kong temperature data and line-chart example because it was only an example and did not represent my chosen phenomenon. I replaced it with bird occurrence data from GBIF and used a bar chart that better fits categorical species counts.