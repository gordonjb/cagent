# Setup & Configuration

- [Naming files](#naming-files)
  - [But I don't wanna rename my files!](#but-i-don-t-wanna-rename-my-files-)
- [Adding a new Wrestling library](#adding-a-new-wrestling-library)
- [Enable local poster files](#enable-local-poster-files)
- [Manual matching](#manual-matching)
  - [Match an item using an ID](#match-an-item-using-an-id)
    - [Match an event](#match-an-event)
    - [Match a match](#match-a-match)
  - [Match an item against another agent](#match-an-item-against-another-agent)
- [Configuration items](#configuration-items)
  - ["Add matched events to a \"Promotion Name\" collection"](#-add-matched-events-to-a---promotion-name---collection-)
  - ["Add individual matches to a \"Promotion Name\" collection"](#-add-individual-matches-to-a---promotion-name---collection-)
  - ["Add individual matches to a \"Matches\" collection"](#-add-individual-matches-to-a---matches---collection-)
  - ["Card information to be included in the event description: "](#-card-information-to-be-included-in-the-event-description---)
  - ["Maximum number of reviews to add (0 disables reviews)"](#-maximum-number-of-reviews-to-add--0-disables-reviews--)
  - ["Include WON Ratings if available when adding reviews (no effect if reviews are disabled)"](#-include-won-ratings-if-available-when-adding-reviews--no-effect-if-reviews-are-disabled--)
  - ["Remove promotion abbreviaton from event titles: "](#-remove-promotion-abbreviaton-from-event-titles---)

## Naming files

In order to auto match files to events and matches, CAGEnt expects files to be named a certain way, much like Plex does. The following is the folder structure I use, and therefore what CAGEnt was built around.

Events are named with the following structure:

```sh
{Promotion initials} - YYYY-MM-DD - {Event name}/{Promotion initials} - YYYY-MM-DD - {Event name}.ext
```

Freelance events without an associated promotion have the initial section removed:

```sh
YYYY-MM-DD - {Event name}/YYYY-MM-DD - {Event name}.ext
```

Matches are placed in the root folder instead of inside named folders like events are (although there's no reason they can't be placed in individual folders like events if you want). They are named with the following structure (note the `- M -` indicating to CAGEnt that this item should be treated as a match):

```sh
{Promotion initials} - YYYY-MM-DD - M - {Match name}.ext
```

In my opinion, the advantage of this format is that all files from a promotion are naturally grouped together, then ordered by date. It also gives us the information we require to attempt to match the event against CAGEMATCH's database: a date the item occured on, and an event name (the promotion initials + the event name) or match (plus associated promotion) to look for.

Other files, such as DVDs or compilations, that you don't expect to auto match can be named however you like, but should be contained in individual folders as Plex expects Movie items to be. If you want to match them against another agent, name them how Plex would expect for that agent.

### But I don't wanna rename my files!

If you have an organisation system for your wrestling that you prefer, you don't *have* to name your files this way, you can always match manually, using either [ID matching](#match-an-item-using-an-id) or by formatting a search string in the expected filename style. There is however the potential, as we're using Plex's built in file scanner intended for movies, that your folder structure will confuse Plex and not all your files will be found.

If you have a system that works for you, please mention it in this issue ([#14](https://github.com/gordonjb/cagent/issues/14)) and it may be considered for future improvements.

## Adding a new Wrestling library

1. Add a new Plex Films library:
\
![Screenshot of Plex's Add Library screen](/.img/config/addlibrarytype.png)
1. Add your media folders:
\
![Screenshot of Plex's Add Folder screen](/.img/config/addlibraryfolder.png)
1. **Manually** select "Advanced" from the sidebar on the left instead of "Add Library" on the bottom right:
\
![Screenshot showing the Advanced option on the sidebar](/.img/config/addlibraryadvanced.jpg)
1. In the "Agent" dropdown, select CAGEnt as the library agent:
\
![Screenshot displaying agent dropdown](/.img/config/addlibraryagent.png)
1. Configure CAGEnt's options to your liking (these can be changed at any time):
\
![Screenshot displaying CAGEnt's settings](/.img/config/addlibrarysettings.png)
1. Set any other library settings, and then "Add Library".

## Enable local poster files

Under your Plex server settings, select "Agents" from the "Settings" section, then under "Films" select the "CAGEnt" tab. You can then tick "Local Media Assets (Movies)". This will allow `poster.ext` and `fanart.ext` files to be used to set posters and backgrounds for library items.
![Screenshot of Plex's Agents screen showing recommended settings](/.img/config/plexsettingsagents.png)

## Manual matching

The below steps will also work to fix incorrect matches. Select "Fix match..." on matched items to reach the same dialog. More general Plex documentation on matching is located [here](https://support.plex.tv/articles/201018497-fix-match-match/) and could be helpful.

### Match an item using an ID

CAGEMATCH doesn't have a general search option that works across matches and events, and what searches it does have are somewhat strict. This means that even perfectly named files won't always be matched or matched correctly. In cases where auto matching or searching isn't giving the desired results, items can be matched using explicit IDs.

#### Match an event

1. Find the correct event page on CAGEMATCH. The event ID number is contained in the URL following `nr=`, for instance for the event [WrestleMania X-7](https://www.cagematch.net/?id=1&nr=2196&page=2), with URL `https://www.cagematch.net/?id=1&nr=2196&page=2`, the event ID is `2196`.
1. Click the three dots on the unmatched item, and click "Match..."
\
![Screenshot showing the match option on an unmatched item](/.img/config/thirdpartymatch.png)
1. Click "Search Options"
1. With the CAGEnt Agent selected, enter the ID in the "Title" field in the format `cm-id:{event-id}`, for instance for our above example enter `cm-id:2196`
\
![Screenshot showing the Fix Match dialog with an ID number entered in the Title field](/.img/config/idevententry.png)
1. Click "Search"
1. There should only be one search result, if it is correct, select it
\
![Screenshot showing the Fix Match dialog search results, with a single result](/.img/config/ideventsearch.png)

#### Match a match

1. Find the correct event page on CAGEMATCH. The event ID number is contained in the URL following `nr=`, for instance for the event [WarGames 1996](https://www.cagematch.net/?id=1&nr=1623), with URL `https://www.cagematch.net/?id=1&nr=1623`, the event ID is `1623`.
1. The match ID is the number of the match in the order on the event page, starting from 1. For this example we'll match the main event War Games match. On the event page, this is match number 8, so the match ID is `8`.
\
**HINT:** There are two other ways of specifying matches.
    - You can use negative numbers to start counting from the end of the list, for example match ID `-1` would be the last match on the card, `-2` second to last, and so on
    - A match ID of `0` will display all the matches on the card
1. Click the three dots on the unmatched item, and click "Match..."
\
![Screenshot showing the match option on an unmatched item](/.img/config/thirdpartymatch.png)
1. Click "Search Options"
1. With the CAGEnt Agent selected, enter the ID in the "Title" field in the format `cm-id:{event-id}:{match-id}`, for instance for our above example enter `cm-id:1623:8`
\
![Screenshot showing the Fix Match dialog with an ID number entered in the Title field](/.img/config/idmatchentry.png)
1. Click "Search"
1. There should only be one search result, if it is correct, select it
\
![Screenshot showing the Fix Match dialog search results, with a single result](/.img/config/idmatchsearch.png)

### Match an item against another agent

CAGEMATCH won't contain information for every event, and sometimes the more mainstream datasources will have preferable or better metadata available, particularly for larger companies, or DVD releases for instance. In these cases, you can manually match items against these databases:

1. Click the three dots on the unmatched item, and click "Match..."
\
![Screenshot showing the match option on an unmatched item](/.img/config/thirdpartymatch.png)
1. Click "Search Options"
1. Pick the agent you want to search against and enter your search text in the "Title" field
\
![Screenshot showing the Fix Match dialog with a search string entered in the Title field and the "The Movie Database" agent selected](/.img/config/thirdpartyselectagent.png)
1. Click "Search"
1. Select the desired match from the results
\
![Screenshot showing the Fix Match dialog search results, with a single result](/.img/config/thirdpartysearch.png)

## Configuration items

### "Add matched events to a \"Promotion Name\" collection"

- **Type:** Tick box (True/False)
- **Default:** False

If true, events will be added to a collection named after the "Promotion" field on the event page.

### "Add individual matches to a \"Promotion Name\" collection"

- **Type:** Tick box (True/False)
- **Default:** False

If true, matches will be added to a collection named after the "Promotion" field on the event page.

### "Add individual matches to a \"Matches\" collection"

- **Type:** Tick box (True/False)
- **Default:** True

If true, matches will be added to a collection named "Matches".

### "Card information to be included in the event description: "

- **Type:** List of options
- **Options:**
  - "Card"
  - "Results"
  - "None"
- **Default:** "Card"

Event summaries can optionally include the following after the initial summary, depending on the option selected here:

- "Card": The results as displayed on an event's "Card" tab (e.g. "x vs y")
- "Results": The results as displayed on an event's "Results" tab (e.g. "y defeats x")
- "None": No card or result information is included in the summary

### "Maximum number of reviews to add (0 disables reviews)"

- **Type:** List of options
- **Options:**
  - "0"
  - "1"
  - "2"
  - ...
  - "20"
- **Default:** "10"

Matched items can contain reviews from CAGEMATCH users. The maximum number of reviews that will be retrieved can be controlled with this setting. Reviews can also be turned off by selecting "0". This setting does not affect the rating score on items.

### "Include WON Ratings if available when adding reviews (no effect if reviews are disabled)"

- **Type:** Tick box (True/False)
- **Default:** True

If true, when adding reviews, the first review will always be the star rating from the Wresting Observer, if one exists on CAGEMATCH for the match.

### "Remove promotion abbreviaton from event titles: "

- **Type:** List of options
- **Options:**
  - "Always"
  - "When added to \"Promotion Name\" collection"
  - "Never"
- **Default:** "When added to \"Promotion Name\" collection"

Event titles on CAGEMATCH include the short promotion name in them, for instance "***WWE*** SummerSlam 2008". The promotion name can be removed, depending on the option selected here:

- "Always": The short name will always be removed from titles (e.g. title will be "Summerslam 2008")
- "When added to \"Promotion Name\" collection": The short name will be removed from titles if that event is going to be added to a \"Promotion Name\" collection (e.g. title will be "Summerslam 2008" if CAGEnt is also going to add it to a "World Wrestling Entertainment" collection)
- "Never": The title will not be changed (e.g. title will be "WWE Summerslam 2008")
