## The Stock Archive

The stock archive is a project to collect and organize financial data from companies. the aspiration is to capture the annual reports for the omxs30 companies for the years 2019-2024. 

First is to create a solid master of all the instruments that is in the scope of this project. I've captued a static version of the table with all the companies that is in scope at first glance, see the OMXS30_members.csv. from the omxs30_members, we will map it to the instrument master, but as of right now, it is missing inforamtion like the investor relations url, which is crucial for us to be able to find the annual reports.


steps:

1. create instrument master for the companies that is in scope
    - go to the [list here](https://www.nasdaq.com/european-market-activity/indexes/omxs30?id=IX447) and capture the table that matches what we have in omxs30_members.csv
    - Using the omxs30_members.csv, map it to the instrument master table using the name. If there is a mismatch, raise an error.
2. From the up to date instrument master we will find the investor_relations_url
    - Here we have to build a scraper that should go and search for the investor relations page based on the company name.
    - go and search the web like this "https://duckduckgo.com/?q=abb+ltd+investor+relations&t=h_&ia=web", adjust it for the company we are looking for
    - take the first result and save it as the investor_relations_url in the instrument master. 
    - valiate that the url contains keywords like "investor" or "ir" to make sure we are on the right page.
    - save it to the instrument master
