# ################### Imports ###################
import urllib
import re
import urlparse
import os

from urllib import url2pathname 
from fuzzywuzzy import fuzz, process
from bs4 import BeautifulSoup, Tag
from url_loading import simple_get
from utils import get_date
from datetime import datetime

# ################### Agent Constants ###################
AGENT_NAME = "CAGEnt"
AGENT_LANGUAGES = [Locale.Language.English]
AGENT_PRIMARY_PROVIDER = True
AGENT_ACCEPTS_FROM = [ 'com.plexapp.agents.localmedia' ]

# ################### URLs ###################
CM_MAIN_URL = "https://www.cagematch.net/"
CM_FROM_YEAR = "1887"
CM_SEARCH_URL = "?id=1&view=search&sEventName={eventname}"
CM_DEFAULT_DATE_PARAMS = "&sDateFromDay=01&sDateFromMonth=01&sDateFromYear=" + CM_FROM_YEAR
CM_SPECIFIC_DATE_PARAMS = "&sDateFromDay={day}&sDateFromMonth={month}&sDateFromYear={year}&sDateTillDay={day}&sDateTillMonth={month}&sDateTillYear={year}"
CM_EVENT_URL = "?id=1&nr={eventid}"
CM_EVENT_CARD_PARAM = "&page=2"
CM_REVIEWS_PARAM = "&page=99"

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
MATCH_KEY = "Match"

# ################### Cagematch matchguide keys ###################
WON_KEY = "WON rating" # Not always present

# ################### the scary regex ###################
# https://regex101.com/r/YgefKe/1
FILENAME_REGEX = "(?:(?=^\d{4})|(?P<prom>.+?)(?:(?= [^-]) |(?= - ) - ))(?P<date>(?:\d{4})(?: |-|.)(?:(?:0[1-9])|(?:1[0-2]))(?: |-|.)(?:(?:0[1-9])|(?:1[0-9])|(?:2[0-9])|(?:3[0-1])))(?:(?= M | - M - )(?P<match> M | - M - )|(?! M | - M - )(?:(?= [^-]) |(?= - ) - ))(?P<name>.+)"
reg = re.compile(FILENAME_REGEX)


# ################### Other Cagematch constants ###################
FREELANCE_STRINGS = ['Wrestling In Mexiko - Freelance Shows', 'Wrestling In Europa - Freelance Shows', 'Wrestling In Japan - Freelance Shows', 'Wrestling In Canada - Freelance Shows', 'Wrestling In Australia - Freelance Shows', 'Wrestling In The USA - Freelance Shows', 'Wrestling Im Rest der Welt - Freelance Shows']


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
    """
    If the provided element is a link, return a dictionary containing the link's display 'text' and the 'link' itself.
    Otherwise return a dictionary with 'text' being the string of the element
    """
    if box_content.name == 'a':
        return {'text': str(box_content.string), 'link': str(box_content.attrs['href'])}
    elif isinstance(box_content, Tag):
        return {'text': box_content.text}
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


def format_match_name_for_candidate(match, event, year, month, day):
    return match + " @ " + event + " - " + year + month + day


class Cagent_Movie(Agent.Movies):
    """
    Agent class to match wrestling shows as Movie library items.
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
        search_str = media.name
        if media.filename:
            pathname = url2pathname(media.filename)
            search_str = os.path.splitext(os.path.basename(pathname))[0]
        Log.Info("[" + AGENT_NAME + "] [search] Searching for \"" + search_str + "\" " + ("manually" if manual else "automatically"))
        # CM ID Regex tester: https://regex101.com/r/6mNdAe/1
        manual_id_match = re.match(r'^cm-id:([0-9]+:?-?[0-9]+)$', search_str)
        if manual_id_match:
            self.search_by_cm_id(results, lang, manual_id_match.group(1))
            return
        else:
            reg_match = reg.match(search_str)
            if reg_match is not None:
                search_input = {k: v for k, v in reg_match.groupdict().items() if v is not None}
                Log.Debug("[" + AGENT_NAME + "] [search] Regex found the following components: " + str(search_input))
            else:
                search_input = {'name': search_str}
            
            if 'match' in search_input:
                self.search_for_matches(results, media, lang, search_input, search_str)
                return
            else:
                # Search for an event
                self.search_for_events(results, media, lang, search_input, search_str)
                return


    def update(self, metadata, media, lang, force):
        Log.Info("[" + AGENT_NAME + "] [update] Updating item with ID: " + metadata.id)
        is_match = False
        if ":" in metadata.id:
            event_id, match_id = metadata.id.split(":")
            is_match = True
        else:
            event_id = metadata.id
        Log.Info("[" + AGENT_NAME + "] [update] Using event ID " + event_id)
        target_url = CM_MAIN_URL + CM_EVENT_URL.format(eventid=event_id)
        Log.Debug("[" + AGENT_NAME + "] [update] Event URL: " + target_url)
        raw_html = simple_get(target_url)
        if raw_html is not None:
            html = BeautifulSoup(raw_html, 'html.parser')
            dictionary = get_event_information_dictionary(html)

            # First do the things that are common between events and matches
            Log.Debug("[" + AGENT_NAME + "] [update] Setting common metadata")
            # Set the event date
            date_str = dictionary.get(BROADCAST_DATE_KEY, dictionary[DATE_KEY])['text']
            if date_str is not None:
                event_date = datetime.strptime(str(date_str), "%d.%m.%Y")
                if event_date is not None:
                    metadata.originally_available_at = event_date

            # Set the "studio" (i.e. Promotion)
            promotion = str(dictionary[PROMOTION_KEY]['text'])
            if promotion is not None and promotion not in FREELANCE_STRINGS:
                metadata.studio = promotion

            # Set up collections
            collections = []
            if promotion is not None and promotion not in FREELANCE_STRINGS:
                if ((is_match and Prefs["addMatchesToPromotionCollection"]) or 
                    (not is_match and Prefs["addEventsToCollection"])):
                    if promotion not in collections: 
                        collections.append(promotion)

            if is_match and Prefs["addMatchesToMatchesCollection"]:
                if "Matches" not in collections: 
                    collections.append("Matches")

            metadata.collections.clear()
            metadata.collections = collections

            if is_match:
                Log.Debug("[" + AGENT_NAME + "] [update] Setting match specific metadata")
                match_idx = int(match_id) - 1
                # For matches, use the match card to get the title and set it into the dictionary
                raw_card_html = simple_get(target_url + CM_EVENT_CARD_PARAM)
                if raw_card_html is not None:
                    card_html = BeautifulSoup(raw_card_html, 'html.parser')
                    card_divs = card_html.find("div", {"class": "Matches"})
                    if match_idx < len(card_divs):
                        match_name = str(card_divs.contents[match_idx].find("div", {"class": "MatchResults"}).text)
                        metadata.title = match_name
                        dictionary[MATCH_KEY] = {'text': match_name}
                
                # Set the Cagematch rating if available
                result_divs = html.find("div", {"class": "Matches"})
                if match_idx < len(result_divs):
                    result_text = result_divs.contents[match_idx].find("div", {"class": "MatchRecommendedLine"}).text
                    prefix = ':::: Matchguide Rating: '
                    if result_text.startswith(prefix):
                        event_rating = result_text[len(prefix):result_text.index(' based on')]
                        metadata.rating = float(event_rating)
                    else:
                        Log.Debug("[" + AGENT_NAME + "] [update] No rating for match")

                # Add reviews if enabled
                metadata.reviews.clear()
                maxReviews = int(Prefs["reviewCount"])
                if maxReviews > 0:
                    reviewsAdded = 0
                    if match_idx < len(result_divs):
                        matchguide_url = CM_MAIN_URL + result_divs.contents[match_idx].find("div", {"class": "MatchRecommendedLine"}).find('a', href=True).attrs['href']
                        Log.Debug("[" + AGENT_NAME + "] [update] Matchguide entry: " + matchguide_url)
                        if Prefs["tokyoDome"]:
                            raw_matchguide_html = simple_get(matchguide_url)
                            if raw_matchguide_html is not None:
                                matchguide_html = BeautifulSoup(raw_matchguide_html, 'html.parser')
                                matchguide_dictionary = get_event_information_dictionary(matchguide_html)
                                if WON_KEY in matchguide_dictionary:
                                    reviewsAdded += 1
                                    r = metadata.reviews.new()
                                    r.author = 'Dave Meltzer'
                                    r.source = 'Wrestling Observer Newsletter'
                                    r.link = 'https://www.f4wonline.com/'
                                    r.text = matchguide_dictionary.get(WON_KEY, {}).get('text', '').replace("*", "★").replace("1/2", "⯪").replace("1/4", "¼").replace("3/4", "¾")
                        
                        if reviewsAdded < maxReviews:
                            raw_match_comments_html = simple_get(matchguide_url + CM_REVIEWS_PARAM)
                            if raw_match_comments_html is not None:
                                match_comments_html = BeautifulSoup(raw_match_comments_html, 'html.parser')
                                comment_divs = match_comments_html.find_all("div", {"class": "Comment"})
                                i = 0
                                while (reviewsAdded < maxReviews and i < len(comment_divs)):
                                    comment = comment_divs[i]
                                    r = metadata.reviews.new()
                                    r.author = comment.find("div", {"class": "CommentHeader"}).text.split(" wrote on ")[0]
                                    r.source = 'CAGEMATCH user'
                                    r.link = matchguide_url + CM_REVIEWS_PARAM
                                    r.text = comment.find("div", {"class": "CommentContents"}).text
                                    i += 1
                                    reviewsAdded += 1

                # Set workers as roles, in future some way to link roles that are same e.g. Dean Ambrose/Jon Moxley
                metadata.roles.clear()
                all_workers = html.find("div", {"class": "Comments Font9"})
                worker_list = [w.strip() for w in all_workers.text.split(",")]
                match_text = dictionary.get(MATCH_KEY, {}).get('text', '')
                for worker in worker_list:
                    # Only add workers in this match, do this the naïve way:
                    if worker in match_text:
                        Log.Debug("[" + AGENT_NAME + "] [update] Setting roles: worker " + worker + " match " + match_text)
                        role = metadata.roles.new()
                        role.name = worker
                
                # Build the summary
                match_summary = self.build_match_summary(dictionary)
                if match_summary is not None:
                    metadata.summary = match_summary
            else:
                Log.Debug("[" + AGENT_NAME + "] [update] Setting event specific metadata")
                # Set the event name
                event_name = str(dictionary[NAME_KEY]['text'])
                if event_name is not None:
                    metadata.title = event_name

                # Set the Cagematch rating if available
                ratings_divs = html.find_all("div", {"class": "RatingsBoxAdjustedRating"})
                for div in ratings_divs:
                    if div.string is not None:
                        event_rating = div.string
                        if event_rating is not None and str(event_rating) != "---":
                            metadata.rating = float(event_rating)

                # Add reviews if enabled
                metadata.reviews.clear()
                maxReviews = int(Prefs["reviewCount"])
                if maxReviews > 0:
                    reviewsAdded = 0
                    raw_event_comments_html = simple_get(target_url + CM_REVIEWS_PARAM)
                    if raw_event_comments_html is not None:
                        event_comments_html = BeautifulSoup(raw_event_comments_html, 'html.parser')
                        comment_divs = event_comments_html.find_all("div", {"class": "Comment"})
                        i = 0
                        while (reviewsAdded < maxReviews and i < len(comment_divs)):
                            comment = comment_divs[i]
                            r = metadata.reviews.new()
                            r.author = comment.find("div", {"class": "CommentHeader"}).text.split(" wrote on ")[0]
                            r.source = 'CAGEMATCH user'
                            r.link = target_url + CM_REVIEWS_PARAM
                            r.text = comment.find("div", {"class": "CommentContents"}).text
                            i += 1
                            reviewsAdded += 1
                
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
                worker_list = [w.strip() for w in all_workers.text.split(",")]
                for worker in worker_list:
                    role = metadata.roles.new()
                    role.name = worker
                
                # Build the summary
                event_summary = self.build_event_summary(dictionary)
                if event_summary is not None:
                    metadata.summary = event_summary
        else:
            Log.Error("[" + AGENT_NAME + "] [update] Nothing was returned from request")
        return
    

    def build_event_summary(self, dict):
        DEFAULT_FORMAT_STRING = "{name} was an event {promotion} that took place on {date} from the {arena} in {location}."
        if Prefs["descriptionType"] == 'Card':
            card_str = "{card}"
        elif Prefs["descriptionType"] == 'Results':
            card_str = "{results}"
        elif Prefs["descriptionType"] == 'None':
            card_str = ''
        format_str = DEFAULT_FORMAT_STRING + card_str
        promotion_text = ''
        if dict[PROMOTION_KEY]['text'] not in FREELANCE_STRINGS:
            promotion_text  = 'by ' + dict[PROMOTION_KEY]['text']
        return format_str.format(
            name=dict[NAME_KEY]['text'],
            promotion=promotion_text,
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


    def build_match_summary(self, dict):
        DEFAULT_FORMAT_STRING = "{match_name} was a match at {name}, an event {promotion} that took place on {date} from the {arena} in {location}."
        format_str = DEFAULT_FORMAT_STRING
        promotion_text = ''
        if dict[PROMOTION_KEY]['text'] not in FREELANCE_STRINGS:
            promotion_text  = 'by ' + dict[PROMOTION_KEY]['text']
        return format_str.format(
            name=dict[NAME_KEY]['text'],
            promotion=promotion_text,
            date=dict[DATE_KEY]['text'],
            arena=dict[ARENA_KEY]['text'],
            location=dict[LOCATION_KEY]['text'],
            type=dict[TYPE_KEY]['text'],
            broadcast_type=dict.get(BROADCAST_TYPE_KEY, {}).get('text', ''),
            broadcast_date=dict.get(BROADCAST_DATE_KEY, {}).get('text', ''),
            network=dict.get(NETWORK_KEY, {}).get('text', ''),
            commentary=dict.get(COMMENTARY_KEY, {}).get('text', ''),
            match_name=dict.get(MATCH_KEY, {}).get('text', ''))


    # Request card page, and either return a single candidate: either the event information or the information for a specific match
    def search_by_cm_id(self, results, lang, cm_id):
        Log.Info("[" + AGENT_NAME + "] [search_by_cm_id] Using CAGEMATCH ID " + cm_id)
        event_id = None
        match_id = None
        if ":" in cm_id:
            event_id, match_id = cm_id.split(":")
        else:
            event_id = cm_id
        target_url = CM_MAIN_URL + CM_EVENT_URL.format(eventid=event_id) + CM_EVENT_CARD_PARAM
        Log.Debug("[" + AGENT_NAME + "] [search_by_cm_id] Event URL: " + target_url)
        raw_html = simple_get(target_url)
        if raw_html is not None:
            html = BeautifulSoup(raw_html, 'html.parser')
            dictionary = get_event_information_dictionary(html)
            date_str = dictionary[DATE_KEY]['text']
            dd, mm, yyyy = date_str.split(".")
            event_name = str(dictionary[NAME_KEY]['text'])
            if match_id is not None:
                card_divs = html.find("div", {"class": "Matches"})
                match_id_int = int(match_id)
                match_idx = match_id_int - 1 if match_id_int > 0 else match_id_int
                if match_idx == 0:
                    for count, div in enumerate(card_divs.contents, start=1):
                        name = format_match_name_for_candidate(
                            str(div.find("div", {"class": "MatchResults"}).text),
                            event_name, yyyy, mm, dd)

                        results.Append(MetadataSearchResult(
                            id=event_id + ":" + str(count),
                            name=name,
                            year=str(int(yyyy)),
                            score=50,
                            lang=lang))
                elif match_idx < len(card_divs):
                    name = format_match_name_for_candidate(
                        str(card_divs.contents[match_idx].find("div", {"class": "MatchResults"}).text),
                        event_name, yyyy, mm, dd)

                    results.Append(MetadataSearchResult(
                        id=cm_id,
                        name=name,
                        year=str(int(yyyy)),
                        score=100,
                        lang=lang))
            else:
                results.Append(MetadataSearchResult(
                id=cm_id,
                name=event_name,
                year=str(int(yyyy)),
                score=100,
                lang=lang))
        else:
            Log.Error("[" + AGENT_NAME + "] [search_by_cm_id] Nothing was returned from request")
            return

    
    def search_for_events(self, results, media, lang, search_input, search_input_str):
        search_str = search_input_str
        if 'name' in search_input:
            search_str = search_input['name']
            if 'prom' in search_input:
                search_str = search_input['prom'] + " " + search_str

        if 'date' in search_input:
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


    # Try and find a promotions event(s) on a specific date so we can try match to a specific match
    def search_for_matches(self, results, media, lang, search_input, search_input_str):
        search_str = search_input_str
        if 'prom' in search_input:
            search_str = search_input['prom']

        if 'date' in search_input:
            date = get_date(search_input['date'])
            candidate_events = self.do_event_search(search_str, date)
        match_candidates = []
        for candidate in candidate_events:
            target_url = CM_MAIN_URL + CM_EVENT_URL.format(eventid=candidate['id'])
            raw_card_html = simple_get(target_url + CM_EVENT_CARD_PARAM)
            if raw_card_html is not None:
                card_html = BeautifulSoup(raw_card_html, 'html.parser')
                card_divs = card_html.find("div", {"class": "Matches"})
                match_candidates = []
                match_index = 1
                for div in card_divs:
                    match_candidates.append(
                        {
                            'id': candidate['id'] + ":" + str(match_index),
                            'name': str(div.find("div", {"class": "MatchResults"}).text),
                            'event_name': candidate['name'],
                            'year': candidate['year'],
                            'month': candidate['month'],
                            'day': candidate['day']
                        }
                    )
                    match_index = match_index + 1

        # Try to match candidate matches to the extracted name component
        match_str = search_input_str
        if 'name' in search_input:
            match_str = search_input['name']
        scored_candidates = process.extract(match_str, [c['name'] for c in match_candidates], limit=len(match_candidates), scorer=fuzz.token_set_ratio)
        score_dict = dict(scored_candidates)
        Log.Debug("[" + AGENT_NAME + "] [search_for_matches] Candidate scores ratio: " + str(score_dict))
        # TODO do some scoring modification for date matches: promotion match and date match
        for candidate in match_candidates:
            Log.Debug("[" + AGENT_NAME + "] [search_for_matches] Adding candidate: " + str(candidate))
            results.Append(MetadataSearchResult(
                id=candidate['id'],
                name=format_match_name_for_candidate(candidate['name'], candidate['event_name'], candidate['year'], candidate['month'], candidate['day']),
                year=candidate['year'],
                score=score_dict[candidate['name']],
                lang=lang))
                
        return


    def do_event_search(self, search_str, date=None):
        Log.Info("[" + AGENT_NAME + "] [do_event_search] Performing search with string \"" + search_str + "\"")
        safe_url = urllib.quote_plus(search_str)
        target_url = CM_MAIN_URL + CM_SEARCH_URL.format(eventname=safe_url)
        if date is not None:
            target_url = target_url + CM_SPECIFIC_DATE_PARAMS.format(day=date.day,month=date.month,year=date.year)
        else:
            target_url = target_url + CM_DEFAULT_DATE_PARAMS
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
