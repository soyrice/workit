import re
import json
import requests
import pandas as pd

# query # of establishments from bls qcew and census nonemployer statistics
# aggregate yearly averages for total # of establishments into one dataframe
class get(object):
    """
    Use variables from getVariables to query BLS QWEC and nonemployer APIs

    attributes: list of seriesIDs, start year, end year, state, naics industry code
    """

    def __init__(self, seriesList, start, end, agg='none'):
        
        # initialize variables defined in inputSeries() and accept start and end year
        # initialized variables are used to query data directly from API calls
        self.seriesList = seriesList
        self.start = start
        self.end = end
        self.headers=[]
        self.dfQ = pd.DataFrame()
        self.dfN = pd.DataFrame()
        self.df = pd.DataFrame()

        self.agg=agg
        self.statesAgg={}

        # find all seriesIDs associated with the state, naics combination and
        # reassign seriesList with the list of seriesIDs

        # parse input to get each state+naics combination
        # inputs are in the form [str(state), int(naics), int(naics)... str(state)...]
        # get 2-digit code for each state in input
        statesURL = 'https://script.google.com/macros/s/AKfycbxYuzwcZe6pmlx-fBCeThSbufUvmxeScFy7B4Thf0n34ozIcNk/exec?'
        statesParams = {}
        stateNames = re.findall("'([A-Za-z]+)'", str(self.seriesList))
        if len(stateNames) > 0 :
            for count in range(0,len(stateNames)) :
                statesParams['state%s'%(count)] = stateNames[count]

            content = requests.get(statesURL, params=statesParams).json()
            for stateName in content.keys() :
                for counter in range(0,len(self.seriesList)) :
                    if stateName == self.seriesList[counter] :
                        self.seriesList[counter] = content[stateName]

            # convert list object into a string to allow regex to parse
            # states are only string inputs and are two characters long
            inputsList = []
            states = re.findall("'([0-9]{2})'", str(self.seriesList))
            for count in range(0, len(states)) :
                try :
                    naicsList = re.findall("%s(.*)%s"%(states[count], states[count+1]), str(self.seriesList))
                except :
                    naicsList = re.findall("%s(.*)]"%(states[count]), str(self.seriesList))

                inputsList.append(('%s'%(states[count]), re.findall("[0-9]+", str(naicsList))))

            # for a given state+naics get all seasonally unadjusted ids
            # for size=establishments, type=all establishments, and each possible ownership codes
            self.seriesList = []
            inputsDict = dict(inputsList)
            for state in inputsDict.keys() :
                for naics in inputsDict[state] :
                    self.seriesList.append('ENU'+state+'0002'+'0'+'1'+naics)
                    self.seriesList.append('ENU'+state+'0002'+'0'+'2'+naics)
                    self.seriesList.append('ENU'+state+'0002'+'0'+'3'+naics)
                    self.seriesList.append('ENU'+state+'0002'+'0'+'4'+naics)
                    self.seriesList.append('ENU'+state+'0002'+'0'+'5'+naics)

    # query data from BLS API version 2.0
    # query is based on example code at http://www.bls.gov/developers/api_python.htm#python2    
    def blsQuery(self):

        blsURL = 'http://api.bls.gov/publicAPI/v2/timeseries/data/'
        headers = {'Content-type': 'application/json'}
        data = json.dumps({"seriesid": self.seriesList,"startyear":self.start, "endyear":self.end})
        content = requests.post(blsURL, data=data, headers=headers)
        json_data = json.loads(content.text)
        df = pd.DataFrame()
        headersUnique = []
        
        # fill dataframe with # of establishments from json payload
        # parse the data based on Python 2.x example in the link above
        for series in json_data['Results']['series'] :
            
            seriesID = series['seriesID']
            state = re.findall('[A-Z]([0-9]{2})', seriesID)[0]
            naics = seriesID[11:]
            if state+naics not in self.headers :
                headersUnique.append(state+naics)
            self.headers.append(state+naics)
            d = {}
            yArray = []

            for item in series['data'] :
                year = item['year']
                period = item['period']
                value = item['value']

                if value.isalpha() == False :
                    if '1' in period :
                        yArray.append(int(value))
                        d[year] = yArray
                        yArray = []

                    else :
                        yArray.append(int(value))
    
            # calculate avg number of establishments per year
            # in time series for each seriesID (row = year, column = seriesID)
            df = pd.concat([df, pd.DataFrame(d, index=['Q1','Q2','Q3','Q4']).mean()], axis=1).round()
            # format rounded average w/o decimals
            # formatting modified from http://stackoverflow.com/a/21291622
            pd.options.display.float_format = '{:.0f}'.format

        # combine columns with data for same naics in same state, but different owners or sizes
        # output is a dataframe with a column for # establishments in each unique naics, state combination
        df.columns = self.headers
        for header in headersUnique :
            try :
                self.dfQ = pd.concat([self.dfQ, df[header].sum(axis=1)], axis=1)
            except :
                self.dfQ = pd.concat([self.dfQ, df[header]], axis=1)
        self.dfQ.columns = headersUnique

    # query data from Census nonemployer statistics API at 
    # http://www.census.gov/data/api/available/nonemployer-statistics-and-county-business-patterns.html
    def nonempQuery(self):

        # query each year in time series individually and aggregate each query into one dataset
        # add nonemployer data to data frame for each year in the time series
        yearList=range(self.start,self.end+1)
        headersUnique = []
        
        for series in self.seriesList :
                
            # get naics, state industry code from seriesID, initialize dict of establishments per year
            # seriesID format at http://www.bls.gov/help/hlpforma.htm#EN
            state = re.findall("[A-Z]([0-9]{2})", series)[0]
            naics = series[11:]
            if state+naics not in headersUnique :
                headersUnique.append(state+naics)
                dN = {}

                for year in yearList:

                    if year >= 2008 :

                        nonempURL = 'http://api.census.gov/data/%s/nonemp?'%(year)

                        if year > 2011 :
                            nonempParams = {'get': 'NESTAB',
                            'for': 'county:*',
                            'in': 'state:%s'%(state),
                            'NAICS2012': naics}

                        else :
                            nonempParams = {'get': 'NESTAB',
                            'for': 'county:*',
                            'in': 'state:%s'%(state),
                            'NAICS2007': naics}

                        dN[str(year)] = sum(map(int, re.findall('[[]"([0-9]+)"', requests.get(nonempURL,params=nonempParams).content)))

                self.dfN = pd.concat([self.dfN, pd.DataFrame(dN, index=['Q1','Q2','Q3','Q4']).mean()], axis=1)

        self.dfN.columns = headersUnique

    def sumData(self):
        self.blsQuery()
        self.nonempQuery()
        self.df = pd.DataFrame.add(self.dfQ, self.dfN, fill_value=0)
        for column in self.df.columns :
            if self.df[column].sum() == 0 :
                self.df = self.df.drop(column, 1)

        # handle optional parameter to aggregate data
        # optional parameter specifies what level to aggregate data
        # if no level of aggregation is specified then keep the dataframe at
        # the most detailed level of aggregation (state+naics)
        if self.agg == 'none' :
            pass

        # if specified to aggregate by state then identify all the states in the df a
        # and  change their headers from state+naics to just the state
        # to sum over each set of series with the same same header
        elif self.agg.lower() == 'state' :

            headersUnique=[]
            headersState=[]
            dfState = pd.DataFrame()
            # fill an array with the state for each series in df
            # fill another array with the unique states in the dataframe
            for header in self.df.columns :
                headersState.append(header[0:2])
                if header[0:2] not in headersUnique :
                    headersUnique.append(header[0:2])

            # re-assign the column names to the state for which the data is from
            # then sum all columns with the same header (from the same state)
            self.df.columns = headersState
            for header in headersUnique :
                try :
                    dfState = pd.concat([dfState, self.df[header].sum(axis=1)], axis=1)
                except :
                    dfState = pd.concat([dfState, self.df[header]], axis=1)
            dfState.columns = headersUnique

            self.df = dfState

        # if specified to aggregate by naics then identify all the naics in the df
        # in the query from the headers and change their headers from state+naics
        # to just the naics to sum over each set of series with the same same header
        elif self.agg.lower() == 'naics' :

            headersUnique=[]
            headersNaics=[]
            dfNaics = pd.DataFrame()
            # fill an array with the naics for each series in df
            # fill another array with the unique naics in the dataframe
            for header in self.df.columns :
                headersNaics.append(header[2:])
                if header[2:] not in headersUnique :
                    headersUnique.append(header[2:])

            # re-assign the column names to the naics for which the data is from
            # then sum all columns with the same header (in the same naics)
            self.df.columns = headersNaics
            for header in headersUnique :
                try :
                    dfNaics = pd.concat([dfNaics, self.df[header].sum(axis=1)], axis=1)
                except :
                    dfNaics = pd.concat([dfNaics, self.df[header]], axis=1)
            dfNaics.columns = headersUnique

            self.df = dfNaics

    def __repr__(self):
        if len(self.df) == 0 :
            self.sumData()
        return self.df.to_string()

# export dataframe as CSV
# if tableau parameter is specified then export data formatted for tableau
def export(data, tableau='none'):
    import time
    
    # initialize dataframe if object hasn't been called
    # otherwise function will export an empty csv
    if len(data.df) == 0 :
        data.sumData()

    # export dataframe as csv with a unique file name
    # if tableau param is specified then transpose dataframe into a format
    # that can be imported directly into tableau for visualization
    if tableau[0].lower() == 't' :

        # create a column for each row's header repeated over each row in column
        # create a column for the year of each row's data repeated over the timeseries for each state/naics
        s = data.df.iloc[0]
        for i in range(1,len(data.df.columns)-1) :
            s = s.append(data.df.iloc[i])
        dfT = pd.concat([pd.DataFrame(list(data.df.index)*len(data.df.columns), index=s.index), s], axis=1)

        with open(time.strftime('%a_%H_%M_%S')+'.csv', 'wr') as textFile :
            dfT.to_csv(textFile, index_label='code', header=['year','establishments'])

    else : 
        with open(time.strftime('%a_%H_%M_%S')+'.csv', 'w') as textFile :
            data.df.to_csv(textFile, index_label='year')
            
def stateToCode(state):
    stateShort = {'AK': '02','AL': '01','AR': '06','AZ': '04','CA': '08','CO': '09','CT': '10',
 'DC': '12','DE': '11','FL"': '13','GA': '15','HI': '16','IA': '17','ID': '18',
 'IL': '19','IN': '20','KS': '21','KY': '22','LA': '23','MA': '26','MD': '25',
 'ME': '24','MI': '27','MN': '28','MO': '30','MS': '29','MT': '31','NC': '38',
 'ND': '39','NE': '32','NH': '34','NJ': '35','NM': '36','NV': '33','NY': '37',
 'OH': '40','OK': '41','OR': '42','PA': '43','PR': '72','RI': '44','SC': '45',
 'SD': '46','TN': '47','TX': '48','UT': '49','VI': '78','VT': '50','WA': '53',
 'WI': '55','WV': '54','WY': '56'}
    
    stateLong = {'alaska': '02','alabama': '01','arkansas': '06','arizona': '04','california': '08',
                 'colorado': '09','connecticut': '10','district of columbia': '12','delaware': '11',
                 'florida"': '13','georgia': '15','hawaii': '16','iowa': '17','idaho': '18','illinois': '19',
                 'indiana': '20','kansas': '21','kentucky': '22','louisiana': '23','massachusetts': '26','maryland': '25',
                 'maine': '24','michigan': '27','minnesota': '28','missouri': '30','mississippi': '29','montana': '31',
                 'north carolina': '38','north dakota': '39','nebraska': '32','new hampshire': '34','new jersey': '35',
                 'new mexico': '36','nevada': '33','new york': '37','ohio': '40','oklahoma': '41','oregon': '42',
                 'pennsylvania': '43','puerto rico': '72','rhode island': '44','south carolina': '45'
                 'south dakota': '46','tennessee': '47','texas': '48','utah': '49','virgin islands': '78','vermont': '50',
                 'washington': '53','wisconsin': '55','west virginia': '54','wyoming': '56'}
    
    for state in states :
        if state in stateShort.keys() :
            code = stateShort[state]
        elif state.lower() in stateLong.keys() :
            code = stateLong[state]
            
    return code
