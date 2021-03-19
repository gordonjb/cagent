# CAGEnt - Plex Metadata Agent for CAGEMATCH.net

CAGEnt is a Plex metadata agent for the incredible wrestling database, CAGEMATCH.net. CAGEnt will attempt to match files in Movie libraries against Event entries in the CAGEMATCH database, providing metadata where possible.

## How does it work?

We use a few things to perform different functions:

- requests to retrieve raw HTML
- BeautifulSoup to parse the raw HTML
- fuzzywuzzy to score search results

## Why does this exist?

If you search around, you'll find quite a few posts where people discuss how they organise their wrestling libraries. Mostly, these posts conclude that there isn't a great option. While WWE got some coverage in existing metadata DBs, it was often prone to being deleted at a moment's notice on the whims of the admin. While that situation seems to have alleviated of late, and weekly TV is represented in TVDB and elsewhere, the volume of wrestling available means that not everything is going to be available in a DB intended to track TV Shows and Movies, and arguably every wrestling event doesn't fit in a database like that.

My previous setup had just been to dump files in a folder and use the "Other Videos" library type in Plex, which doesn't provide any of the niceties like metadata or a nice way to sort files. Due to... incidents... I'd checked out of wrestling for most of 2020, and recently decided to build a new library of wrestling content. I wanted a library that looked nice, was sorted well and had metadata defined. After matching some ROH content that *was* included in TMDB, I thought building a Plex agent that could do the same for any wrestling event would be a fun project. I also had Python experience scraping CAGEMATCH for a previous project, [graplist.fm](https://github.com/gordonjb/graplist.fm), sadly abandoned around the time it turned out half my top 10 had been noncing.

## Do you like this?

In lieu of donating to me, please support CAGEMATCH, as it's their bandwidth we're using, to keep their incredible dataset online. They have a Patreon at <https://www.patreon.com/cagematchdotnet>.
