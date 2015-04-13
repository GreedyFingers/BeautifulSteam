import pdb
import sys
import json
import os
import inspect
import re
import urllib2
from bs4 import BeautifulSoup

#output file location
dir = os.path.dirname(inspect.getfile(inspect.currentframe()))

#Open URL and get DOM objects
def getSteamSoup(url):
    opener = urllib2.build_opener()
    #You can get your own birthtime cookie by visiting an age restricted
    #Steam app page
    opener.addheaders.append(('Cookie', 'birthtime=644310001'))
    #some URLs have redirect loops
    try:
        f = opener.open(url)
    except urllib2.HTTPError, err:
        return ""
    
    #perform magic
    soup = BeautifulSoup(f.read())
    return soup

def parse_steam(url):
    print 'Parsing elements from ' + url + ' ...'
    soup = getSteamSoup(url)

    #If URL successfully opened...
    if soup and len(soup) > 1 :   
        
        #Get App name
        appNameElem = soup.find_all("div",class_ = "apphub_AppName")
        
        #this will catch if the current Steam app URL redirects to any page
        #that isn't really an app (eg Steam store page, regional error, promotional video, etc)
        if len(appNameElem) > 0:
            appName = appNameElem[0].text.encode('ascii', 'backslashreplace')
        else:
            return {}

        #ID number that is standard identifier for all apps
        gameID = re.search('[0-9]+',url).group(0)     
            
        #Get all user defined tags (only most popular tags appear on page)
        tags = ""        
        tagCount = 0
        for tag in soup.find_all("a",class_ = "app_tag" ):
            for string in tag.stripped_strings:
                tags = tags + string + ","
                tagCount = tagCount+1
        tags = tags[:len(tags)-1]

        negativeCount = ""
        positiveCount = "" 
        #Occasionally Steam will, for whatever reason, show the filters as "Show Only Positive"
        #or "Show Only Negative", instead of the usual "Positive (##)", "Negative (##)" filter names,
        #which is what this part is looking for to get a count. In that case, the only apparent solution
        #is to just keep refreshing the page until it gives what we need
        noReviewsYet = soup.find_all("div", class_ = "noReviewsYetTitle")
        if len(noReviewsYet) < 1:
            pageRefresh = True
            while pageRefresh:
                #Each filter label has a user_reviews_count span that is the actual count, so have to looking
                #at the parent DOM element to figure out whether it's for positive or negative, etc.
                for filter in soup.select(".user_reviews_count"):  
                    reviewCategory = str(filter.parent.span.text).replace(' ','')
                    if (reviewCategory == 'Positive'):
                        positiveCount = filter.text[1:len(filter.text)-1]
                        positiveCount = int(positiveCount.replace(',', ''))
                    elif (reviewCategory == 'Negative'):                 
                        negativeCount = filter.text[1:len(filter.text)-1]
                        negativeCount = int(negativeCount.replace(',', ''))
                    else:
                        continue
                if positiveCount == "" or negativeCount == "":
                    soup = getSteamSoup(url)
                    pageRefresh = True                    
                else:
                    pageRefresh = False
            
            #derive total number of reviews
            totalReviewCount = int(positiveCount) + int(negativeCount)

            #percent recommended
            recommendedRatio = round(float(positiveCount)/float(totalReviewCount),2)
        else:
            totalReviewCount = ""
            recommendedRatio = ""
            
        #some games have metacritic scores
        metacriticScore = soup.find_all(id = "game_area_metascore")
        if len(metacriticScore) > 0 and str(metacriticScore[0].text) != 'NA':
            metaScore = int(metacriticScore[0].span.text)
        else:
            metaScore = ""
        #return JSON object
        return {
            'game_ID': gameID,
            'app_name' : appName,
            'tags': tags,
            'tagCount': tagCount,
            'positive_reviews': positiveCount,
            'negative_reviews': negativeCount,
            'total_reviews': totalReviewCount,
            'recommended_ratio': recommendedRatio,
            'metacritic_score': metaScore,
            'URL': url
            }
    else:
        #something went wrong, so don't get any JSON for this appID
        return {}

#eventually replace with getopt for better argument handling...
if (len(sys.argv) < 2):
    print('Provide path to file of Steam URLs')
else:
    #open txt file list of URLs to parse
    try:
        steamURLList = open(sys.argv[1],'r')
    except IOError:
        print 'cannot open', sys.argv[1]
    else:
    
        #This will concat all JSON objects
        dataList = []    
    
        #Begin the parsing! Go through every URL
        URL = steamURLList.readline().rstrip()
        while str(URL) != '':
            data = parse_steam(URL)
            dataList.append(data)
            URL = steamURLList.readline().rstrip()
            print json.dumps(data, indent=4)   
        steamURLList.close()
        
        #write out contents (use something like http://www.convertcsv.com/json-to-csv.htm 
        #to put this into csv so you can paste it into excel or something)
        with open(os.path.join(dir,'SteamData.txt'), 'w') as outfile:
            json.dump(dataList, outfile)        
    