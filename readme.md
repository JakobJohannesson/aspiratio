## The Stock Archive

The stock archive is a project to collect and organize financial data from companies. The aspriration is to cover as much historical data as possible and to make it easily accessible for analysis. at first, the focus will be on large cap in sweden. we will only focus on capturing the annual reports.

First is to create a solid master of all the instruments that is in the scope of this project. We are looking for all companies that is on the stock exchange in Sweden, starting with large cap companies. The instrument master table should contain company name, ticker symbol, exchange, ISIN code, sector classification, link to investor relations page, next capture date. We also want to capture the identifers to other services like S&P, borsdata and others that might be relevant. We will also create our own issuer id that will be used to link all data that is being captured about the companies. 

Metadata about what we have captured data for all the metrics. we will also make sure we capture what date we captured the data, what agent did the capture and from what source. we will create a unique id, which will be used to identify rows of the datapoints that we capture.

Most of the information should only be captured once, like historical annual reports. Some data should be captured on a regular basis, like quarterly reports, stock price and other financial KPIs that is being reported on a regular basis.

Github action runners will be used to schedule and run the data capture jobs. For each of the sessions, it is important that we log what data that was captured, from what source, when it was captured and by what agent. This is the second step, as the first step will be create a sample of the instrument master and then capture as much information as possible for a small set of companies to validate the approach.

The third step will be be to create the validators so we can make sure that the data is being captured in the right format. 

fourth step will be to create the github action runners, set up and make the data capture jobs to run and fetch the information from the investor relations pages. 


Data that is in scope of this project:

* annual reports
* OMSx30 companies, see the [list here](https://www.nasdaq.com/market-activity/index/omxs30)