# About
A Python wrapper for the getting establishments data from the Bureau of Labor Statistics Quarterly Census of Employment and Wages API and the US Census Nonemployer Statistics and County Business Patterns API. It uses requests and regex to collect and scrape the data, and manages the data with `pandas`.

# Install
1. Download or clone the project

2. From your Python shell or file, import `workit.py` from its local directory:

```python
import C:\file\path\workit.py
```

# Try it out

## Find the number of establishments in each state/naics over the designated time period

Enter a query into the get() class in workit to return the number of establishments in each state/naics over the designated time period:

```python
data = get([‘seriesID’, ‘seriesID’…], start year, end year)
```

where 2015 > end year > start year > 2007, since the nonemployer API gets data between 2008 and 2014. (It only supports NAICS2007 and NAICS2011 classifications.) Instead of seriesIDs, `get()` also accepts a list of state abbreviations, names, or FIPS codes as strings, each followed by the respective integer list of NAICS codes:

```python
data = get(['RI', 1012, 54, 'Massachusetts', 54, '25', 1021, 54, '09', 1021, '23', 54], 2011, 2014)
```

## Find the number of establishments in each state or in each naics over the designated time period

`get()` automatically aggregates by state/naics, the smallest level of aggregation available after querying both APIs. It supports aggregation by state or naics alone:

```python
data1 = get(['ENU440002021012', 'ENU440002031012’, ‘ENU440002031021'], 2009, 2015, agg=‘state’)
data2 = get(['ENU440002021012', 'ENU440002031012’, ‘ENU440002031021'], 2009, 2015, agg=‘naics’)
```

## Print and review the API response

get() prints a string representation of the combined dataframe such that:

```python
data
data.df
```

## Manage the API response as a dataframe

get() returns a class object that with options to view the dataframe built from either the BLS QWEC or nonemployer APIs:

```python
data.dfQ
data.dfN
```

returns the same information, but data.df is the true dataframe object and data prints a copy.

## Save your data as a csv

export() saves your dataframe as a csv in your current directory with a timestamp as a unique name. export() uses your column headers as headers in the csv, with a column header ‘years’ inserted above the index of the dataframe:

```python
export(data)
```

export() also reshapes your data into a format that can be brought into Tableau and visualized without any additional work. Just enter ‘t’ or ‘tableau’ into the tableau parameter. The parameter is not case sensitive:

```python
export(data, tableau=‘t’) # or -->
export(data, tableau=‘tableau’)
