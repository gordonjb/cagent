# ################### Imports ###################
import urllib
import re
import urlparse

from fuzzywuzzy import process
from bs4 import BeautifulSoup
from url_loading import simple_get

# ################### Constants ###################
AGENT_NAME = "CAGEnt"
AGENT_VERSION = "v0.1.0"
AGENT_LANGUAGES = [Locale.Language.English]
AGENT_PRIMARY_PROVIDER = True
AGENT_ACCEPTS_FROM = [ 'com.plexapp.agents.localmedia', 'com.plexapp.agents.opensubtitles', 'com.plexapp.agents.subzero' ]

# ################### URLs ###################
CM_MAIN_URL = "https://www.cagematch.net/"
CM_FROM_YEAR = "1887"
CM_SEARCH_URL = "?id=1&view=search&sEventName={eventname}&sDateFromDay=01&sDateFromMonth=01&sDateFromYear=" + CM_FROM_YEAR
CM_EVENT_URL = "?id=1&nr={eventid}"

# ################### Cagematch keys ###################
DATE_KEY = "Date"
NAME_KEY = "Name of the event"

# ################### the scary regex ###################
# https://regex101.com/r/YgefKe/1
FILENAME_REGEX = "(?:(?=^\d{4})|(?P<prom>.+?)(?:(?= [^-]) |(?= - ) - ))(?P<date>(?:\d{4})(?: |-|.)(?:(?:0[1-9])|(?:1[0-2]))(?: |-|.)(?:(?:0[1-9])|(?:1[0-9])|(?:2[0-9])|(?:3[0-1])))(?:(?= M | - M - )(?P<match> M | - M - )|(?! M | - M - )(?:(?= [^-]) |(?= - ) - ))(?P<name>.+)"
reg = re.compile(FILENAME_REGEX)

def get_event_information_dictionary(html):
    """
    Find the information box from the event page. Essentially treat it as a table:
        - find every InformationBoxTitle div, and use the text as a key.
        - find every InformationBoxContents div, and use the content as a value.

    :param html: the event page html, as parsed through Beautiful Soup
    :return: dictionary of the event information box
    """
    event_table = html.find("div", {"class": "InformationBoxTable"})
    keys = [span.get_text().rstrip(':').strip() for span in event_table.find_all(
        "div", {"class": "InformationBoxTitle"})]
    values = [span.contents[0] for span in event_table.find_all(
        "div", {"class": "InformationBoxContents"})]
    dictionary = dict(zip(keys, values))
    Log.Debug("[" + AGENT_NAME + "] [get_event_information_dictionary] Parsed event dictionary: " + str(dictionary))
    return dictionary


def parse_search_result_row(table_row):
    """
    Parse a table row from a search page and extract the relevant parts to a dict

    :param table_row: a "tr" element extracted from a table
    :return: dictionary containing event id "id", event name "name", and year of event "year"
    """
    table_cells = table_row.find_all('td')
    dd, mm, yyyy = table_cells[1].text.split(".")
    # The event column can have an event link and a promotion image link, so we need to find the right one.
    # As the image links contain no text, we can do this by checking that link.string isn't None
    links = table_cells[2].find_all('a', href=True)
    for link in links:
        if link.string is not None:
            event_link = link
    
    if event_link is not None:
        event_id = urlparse.parse_qs(urlparse.urlparse(event_link.attrs['href']).query)['nr']
        return {
            'id': str(event_id),
            'name': str(event_link.string),
            'year': str(yyyy),
            'month': str(mm),
            'day': str(dd)
        }
    return None


def parse_search_result_counts(html):
    """
    Figure out how many results our search got by parsing the text above the results table.
        - find the div containing this string, class TableHeaderOff id TableHeader
        - check if this matches the string saying no items were found, if so return 0 results
        - otherwise chunk up the string and return how many results were found, and which are
          being displayed

    :param html: the event page html, as parsed through Beautiful Soup
    :return: dictionary containing:
                 - start: the start position of the results returned
                 - end: the end position of the results returned
                 - total: the total number of results the search found
    """
    # Constants
    NO_RESULTS_STRING = "No items were found that match the search parameters."
    RESULTS_STRING_1 = "Displaying items "
    RESULTS_STRING_2 = " to "
    RESULTS_STRING_3 = " of total "
    RESULTS_STRING_4 = " items that match the search parameters."

    search_results_div = html.find('div', {"class": "TableHeaderOff", "id": "TableHeader"})
    if search_results_div.string is NO_RESULTS_STRING:
        search_results = {
            'start': 0,
            'end': 0,
            'total': 0
        }
    elif search_results_div.string.startswith(RESULTS_STRING_1):
        start, split_1 = search_results_div.string.split(RESULTS_STRING_1,1)[1].split(RESULTS_STRING_2, 1)
        end, split_2 = split_1.split(RESULTS_STRING_3,1)
        total = split_2.split(RESULTS_STRING_4)[0]
        search_results = {
            'start': int(start),
            'end': int(end),
            'total': int(total)
        }
    Log.Debug("[" + AGENT_NAME + "] [parse_search_result_counts] Search returned: " + str(search_results))
    return search_results


class Cagent_Movie(Agent.Movies):
    """
    Agent class to match wrestling shows as Movie library items.

    Attributes
    ----------
    name : str
        first name of the person
    surname : str
        family name of the person
    age : int
        age of the person

    Methods
    -------
    info(additional=""):
        Prints the person's name and age.
    """
    name = AGENT_NAME
    languages = AGENT_LANGUAGES
    primary_provider = AGENT_PRIMARY_PROVIDER
    accepts_from = AGENT_ACCEPTS_FROM

    """
    manual: true/false depending on if the search was invoked manually
    results: array that should be filled with MetadataSearchResult object representing candidates for selection
    media: the input to the search. movie searches, as we use, seem to contain:
        'openSubtitlesHash': uhh i guess a file hash?
        'name': a media search name, as determined by the scanner.
        'year': a file year, as determined by the scanner.
        'filename': the full path of the file.
        'plexHash': some sort of hash for plex
        'duration': the length of the media
        'id': some id}
    """
    def search(self, results, media, lang, manual):
        Log.Info("[" + AGENT_NAME + "] [search] Searching for \"" + media.name + "\"")
        manual_id_match = re.match(r'^cm-id:([0-9]+)$', str(media.name))
        if manual_id_match:
            self.search_by_event_id(results, lang, manual_id_match.group(1))
            return
        else:
            search_input = reg.match(media.name).groupdict()
            Log.Debug("[" + AGENT_NAME + "] [search] Regex found the following components: " + str(search_input))
            
            if search_input['match'] is None:
                # Search for a match, to be implemented
                print("To be implemented")
                return
            else:
                # Search for an event
                self.search_for_events(results, media, lang, search_input)
                return


    def update(self, metadata, media, lang, force):
        # Update metadata
        print("To be implemented")
        return


    def search_by_event_id(self, results, lang, event_id):
        Log.Info("[" + AGENT_NAME + "] [search] Using event ID " + event_id)
        target_url = CM_MAIN_URL + CM_EVENT_URL.format(eventid=event_id)
        Log.Debug("[" + AGENT_NAME + "] [search] Event URL: " + target_url)
        raw_html = simple_get(target_url)
        if raw_html is not None:
            html = BeautifulSoup(raw_html, 'html.parser')
            dictionary = get_event_information_dictionary(html)
            date_str = dictionary[DATE_KEY].get_text()
            dd, mm, yyyy = date_str.split(".")
            results.Append(MetadataSearchResult(
                id=event_id,
                name=str(dictionary[NAME_KEY]),
                year=str(int(yyyy)),
                score=100,
                lang=lang))
        else:
            Log.Error("[" + AGENT_NAME + "] [search] Nothing was returned from request")
            return

    
    def search_for_events(self, results, media, lang, search_input):
        search_str = media.name
        if search_input['name'] is not None:
            search_str = search_input['name']
            if search_input['prom'] is not None:
                search_str = search_input['prom'] + " " + search_str

        safe_url = urllib.quote_plus(search_str)
        target_url = CM_MAIN_URL + CM_SEARCH_URL.format(eventname=safe_url)
        Log.Info("[" + AGENT_NAME + "] [search] Performing search with string \"" + search_str + "\"")
        Log.Debug("[" + AGENT_NAME + "] [search] Search URL: " + target_url)
        raw_html = simple_get(target_url)
        if raw_html is not None:
            html = BeautifulSoup(raw_html, 'html.parser')
            search_results = parse_search_result_counts(html)
            if search_results['total'] is 0:
                Log.Info("[" + AGENT_NAME + "] [search] No results found.")
                return
            else:
                candidates = []
                # Should find results table
                table = html.find('table')
                Log.Debug("[" + AGENT_NAME + "] [dumping_table_text] " + table.text)
                # Get all rows, dropping the header
                table_rows = table.find_all('tr', class_=lambda x: x != 'THeaderRow')
                for table_row in table_rows:
                    candidate = parse_search_result_row(table_row)
                    if candidate is not None:
                        candidates.append(candidate)

                scored_candidates = process.extract(search_str, [c['name'] for c in candidates], limit=len(candidates))
                # Convert scores into a dict so we can do a quick lookup using the event name
                score_dict = dict(scored_candidates)
                Log.Debug("[" + AGENT_NAME + "] [search] Candidate scores: " + str(score_dict))
                for candidate in candidates:
                    Log.Debug("[" + AGENT_NAME + "] [search] Adding candidate: " + str(candidate))
                    results.Append(MetadataSearchResult(
                        id=candidate['id'],
                        name=candidate['name'],
                        year=candidate['year'],
                        score=score_dict[candidate['name']],
                        lang=lang))
                return
        else:
            Log.Error("[" + AGENT_NAME + "] [search] Nothing was returned from request")
            return