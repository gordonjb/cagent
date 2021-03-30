# ################### Imports ###################
import urllib
import re
import urlparse

from fuzzywuzzy import process
from bs4 import BeautifulSoup
from url_loading import simple_get
from utils import get_date
from datetime import datetime

# ################### Constants ###################
AGENT_NAME = "CAGEnt"
AGENT_VERSION = "v0.1.0"
AGENT_LANGUAGES = [Locale.Language.English]
AGENT_PRIMARY_PROVIDER = True
AGENT_ACCEPTS_FROM = [ 'com.plexapp.agents.localmedia', 'com.plexapp.agents.opensubtitles', 'com.plexapp.agents.subzero' ]

# ################### URLs ###################
CM_MAIN_URL = "https://www.cagematch.net/"
CM_FROM_YEAR = "1887"
CM_SEARCH_URL = "?id=1&view=search&sEventName={eventname}"
CM_DEFAULT_DATE_PARAMS = "&sDateFromDay=01&sDateFromMonth=01&sDateFromYear=" + CM_FROM_YEAR
CM_SPECIFIC_DATE_PARAMS = "&sDateFromDay={day}&sDateFromMonth={month}&sDateFromYear={year}&sDateTillDay={day}&sDateTillMonth={month}&sDateTillYear={year}"
CM_EVENT_URL = "?id=1&nr={eventid}"
CM_EVENT_CARD_PARAM = "&page=2"

# ################### Cagematch event info keys ###################
DATE_KEY = "Date"
NAME_KEY = "Name of the event"
PROMOTION_KEY = "Promotion"
TYPE_KEY = "Type"
LOCATION_KEY = "Location"
ARENA_KEY = "Arena"
BROADCAST_TYPE_KEY = "Broadcast type" # Not always present
BROADCAST_DATE_KEY = "Broadcast date" # Not always present
NETWORK_KEY = "TV station/network" # Not always present
COMMENTARY_KEY = "Commentary by" # Not always present
CARD_KEY = "Card"
RESULTS_KEY = "Results"

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
    keys = [str(span.get_text().rstrip(':').strip()) for span in event_table.find_all(
        "div", {"class": "InformationBoxTitle"})]
    values = [get_link_dict(span.contents[0]) for span in event_table.find_all(
        "div", {"class": "InformationBoxContents"})]
    dictionary = dict(zip(keys, values))
    Log.Debug("[" + AGENT_NAME + "] [get_event_information_dictionary] Parsed event dictionary: " + str(dictionary))
    return dictionary


def get_link_dict(box_content):
    if box_content.name == 'a':
        return {'text': str(box_content.string), 'link': str(box_content.attrs['href'])}
    else:
        return {'text': str(box_content)}


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
        event_id = dict(urlparse.parse_qsl(urlparse.urlparse(event_link.attrs['href']).query))['nr']
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
    if search_results_div.string == NO_RESULTS_STRING:
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
            reg_match = reg.match(media.name)
            if reg_match is not None:
                search_input = reg_match.groupdict()
                Log.Debug("[" + AGENT_NAME + "] [search] Regex found the following components: " + str(search_input))
            else:
                search_input = {'name': media.name}
            
            if search_input.get('match') is not None:
                # Search for a match, to be implemented
                print("To be implemented")
                return
            else:
                # Search for an event
                self.search_for_events(results, media, lang, search_input)
                return


    def update(self, metadata, media, lang, force):
        Log.Info("[" + AGENT_NAME + "] [update] Updating item with ID: " + metadata.id)
        #if is event id
        self.update_from_event_id(metadata, media)
        # else if match id
        # self.update_from_match_id(metadata, media)
        return


    def update_from_event_id(self, metadata, media):
        event_id = metadata.id
        is_match = False
        Log.Info("[" + AGENT_NAME + "] [update_from_event_id] Using event ID " + event_id)
        target_url = CM_MAIN_URL + CM_EVENT_URL.format(eventid=event_id)
        Log.Debug("[" + AGENT_NAME + "] [update_from_event_id] Event URL: " + target_url)
        raw_html = simple_get(target_url)
        if raw_html is not None:
            html = BeautifulSoup(raw_html, 'html.parser')
            dictionary = get_event_information_dictionary(html)
                        
            # Set the event name
            event_name = str(dictionary[NAME_KEY]['text'])
            if event_name is not None:
                metadata.title = event_name
            
            # Set the event date
            date_str = dictionary.get(BROADCAST_DATE_KEY, dictionary[DATE_KEY])['text']
            if date_str is not None:
                event_date = datetime.strptime(str(date_str), "%d.%m.%Y")
                if event_date is not None:
                    metadata.originally_available_at = event_date

            # Set the "studio" (i.e. Promotion)
            promotion = str(dictionary[PROMOTION_KEY]['text'])
            if promotion is not None:
                metadata.studio = promotion

            # Set up collections
            collections = []
            if promotion is not None:
                if ((is_match and Prefs["addMatchesToPromotionCollection"]) or 
                   (not is_match and Prefs["addEventsToCollection"])):
                    if promotion not in collections: 
                        collections.append(promotion)
                        Log.Debug("[" + AGENT_NAME + "] [update_from_event_id] added collection")

            if is_match and Prefs["addMatchesToMatchesCollection"]:
                if "Matches" not in collections: collections.append("Matches")
            metadata.collections.clear()
            metadata.collections = collections

            # Set the Cagematch rating if available
            ratings_divs = html.find_all("div", {"class": "RatingsBoxAdjustedRating"})
            for div in ratings_divs:
                if div.string is not None:
                    event_rating = div.string
            if event_rating is not None and str(event_rating)!= "---":
                metadata.rating = float(event_rating)
                metadata.rating_image = R('rating_1.png')

            # Set the results into the event dictionary
            result_divs = html.find("div", {"class": "Matches"})
            event_results = ''
            for div in result_divs:
                event_results = event_results + '\n' + str(div.find("div", {"class": "MatchResults"}).text)
            dictionary[RESULTS_KEY] = {'text': event_results}

            # Set the card into the event dictionary
            raw_card_html = simple_get(target_url + CM_EVENT_CARD_PARAM)
            if raw_card_html is not None:
                card_html = BeautifulSoup(raw_card_html, 'html.parser')
                card_divs = card_html.find("div", {"class": "Matches"})
                event_card = ''
                for div in card_divs:
                    event_card = event_card + '\n' + str(div.find("div", {"class": "MatchResults"}).text)
                dictionary[CARD_KEY] = {'text': event_card}

            # Set workers as roles, in future some way to link roles that are same e.g. Dean Ambrose/Jon Moxley
            all_workers = html.find("div", {"class": "Comments Font9"})
            worker_list = all_workers.text.split(",")
            for worker in worker_list:
                role = metadata.roles.new()
                role.name = worker

            # Build the summary
            event_summary = self.build_summary(dictionary)
            if event_summary is not None:
                metadata.summary = event_summary
        else:
            Log.Error("[" + AGENT_NAME + "] [search_by_event_id] Nothing was returned from request")
        return
    

    def build_summary(self, dict):
        DEFAULT_FORMAT_STRING = "{name} was an event by {promotion} that took place on {date} from the {arena} in {location}."
        if Prefs["descriptionType"] == 'Card':
            card_str = "{card}"
        elif Prefs["descriptionType"] == 'Results':
            card_str = "{results}"
        elif Prefs["descriptionType"] == 'None':
            card_str = ''
        format_str = DEFAULT_FORMAT_STRING + card_str
        return format_str.format(
            name=dict[NAME_KEY]['text'],
            promotion=dict[PROMOTION_KEY]['text'],
            date=dict[DATE_KEY]['text'],
            arena=dict[ARENA_KEY]['text'],
            location=dict[LOCATION_KEY]['text'],
            type=dict[TYPE_KEY]['text'],
            broadcast_type=dict.get(BROADCAST_TYPE_KEY, {}).get('text', ''),
            broadcast_date=dict.get(BROADCAST_DATE_KEY, {}).get('text', ''),
            network=dict.get(NETWORK_KEY, {}).get('text', ''),
            commentary=dict.get(COMMENTARY_KEY, {}).get('text', ''),
            card=dict.get(CARD_KEY, {}).get('text', ''),
            results=dict.get(RESULTS_KEY, {}).get('text', ''))


    def search_by_event_id(self, results, lang, event_id):
        Log.Info("[" + AGENT_NAME + "] [search_by_event_id] Using event ID " + event_id)
        target_url = CM_MAIN_URL + CM_EVENT_URL.format(eventid=event_id)
        Log.Debug("[" + AGENT_NAME + "] [search_by_event_id] Event URL: " + target_url)
        raw_html = simple_get(target_url)
        if raw_html is not None:
            html = BeautifulSoup(raw_html, 'html.parser')
            dictionary = get_event_information_dictionary(html)
            date_str = dictionary[DATE_KEY]['text']
            dd, mm, yyyy = date_str.split(".")
            results.Append(MetadataSearchResult(
                id=event_id,
                name=str(dictionary[NAME_KEY]['text']),
                year=str(int(yyyy)),
                score=100,
                lang=lang))
        else:
            Log.Error("[" + AGENT_NAME + "] [search_by_event_id] Nothing was returned from request")
            return

    
    def search_for_events(self, results, media, lang, search_input):
        search_str = media.name
        if search_input['name'] is not None:
            search_str = search_input['name']
            if search_input.get('prom') is not None:
                search_str = search_input['prom'] + " " + search_str

        if search_input['date'] is not None:
            date = get_date(search_input['date'])
            candidate_events = self.do_event_search(search_str, date)
            if len(candidate_events) == 0:
                # If we didn't get any results for a specific date search, 
                # do a more general one
                candidate_events = self.do_event_search(search_str)
        else:
            candidate_events = self.do_event_search(search_str)

        scored_candidates = process.extract(search_str, [c['name'] for c in candidate_events], limit=len(candidate_events))
        # Convert scores into a dict so we can do a quick lookup using the event name
        score_dict = dict(scored_candidates)
        Log.Debug("[" + AGENT_NAME + "] [search_for_events] Candidate scores: " + str(score_dict))
        # TODO do some scoring modification for date matches: promotion match and date match
        for candidate in candidate_events:
            Log.Debug("[" + AGENT_NAME + "] [search_for_events] Adding candidate: " + str(candidate))
            results.Append(MetadataSearchResult(
                id=candidate['id'],
                name=candidate['name'],
                year=candidate['year'],
                score=score_dict[candidate['name']],
                lang=lang))
        return


    def do_event_search(self, search_str, date=None):
        safe_url = urllib.quote_plus(search_str)
        target_url = CM_MAIN_URL + CM_SEARCH_URL.format(eventname=safe_url)
        if date is not None:
            target_url = target_url + CM_SPECIFIC_DATE_PARAMS.format(day=date.day,month=date.month,year=date.year)
        else:
            target_url = target_url + CM_DEFAULT_DATE_PARAMS
        Log.Info("[" + AGENT_NAME + "] [do_event_search] Performing search with string \"" + search_str + "\"")
        Log.Debug("[" + AGENT_NAME + "] [do_event_search] Search URL: " + target_url)
        raw_html = simple_get(target_url)
        if raw_html is not None:
            html = BeautifulSoup(raw_html, 'html.parser')
            search_results = parse_search_result_counts(html)
            if search_results['total'] == 0:
                Log.Info("[" + AGENT_NAME + "] [do_event_search] No results found.")
            else:
                candidates = []
                # Should find results table
                table = html.find('table')
                # Get all rows, dropping the header
                table_rows = table.find_all('tr', class_=lambda x: x != 'THeaderRow')
                for table_row in table_rows:
                    candidate = parse_search_result_row(table_row)
                    if candidate is not None:
                        candidates.append(candidate)
                return candidates
        else:
            Log.Error("[" + AGENT_NAME + "] [do_event_search] Nothing was returned from request")
            
        return []
