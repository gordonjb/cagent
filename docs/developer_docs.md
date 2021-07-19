# Developer info

## Libraries used

We use a few things to perform different functions:

- requests to retrieve raw HTML
- BeautifulSoup to parse the raw HTML
- fuzzywuzzy to score search results

## Developing

First, clone this repository, and go into the root folder. The plugin itself is all contained in the [`Cagent.bundle`](Cagent.bundle) folder.

The bulk of the code is in [`Contents/Code/__init__.py`](Cagent.bundle/Contents/Code/__init__.py).

To deploy the plugin, you'll need to populate the dependencies of the project. These go in the [`Contents/Libraries/Shared`](Cagent.bundle/Contents/Libraries/Shared) folder. If you already have access to these, either from an existing install on your Plex server or from a release bundle, then you don't need to worry, just copy your updated code into the plugin directory. If you want to update the dependencies, or add new ones, you'll want to grab them again.

**NOTE**: You need to use a 2.7.x version of Python to fetch these dependencies, otherwise pip will fetch 3.x versions of the dependencies that Plex will not understand.

To download the dependencies to this directory, use the following command:

```bash
pip install -t Cagent.bundle/Contents/Libraries/Shared/ --no-compile --no-binary=:all -r requirements.txt
```

To instead download the latest dependency versions, and update the requirements file, use the following commands:

```bash
pip install -t Cagent.bundle/Contents/Libraries/Shared/ --no-compile --no-binary=:all requests beautifulsoup4 fuzzywuzzy
pip freeze --path Cagent.bundle/Contents/Libraries/Shared/ > requirements.txt
```

## Testing in Docker

To test the agent, I use the included [Docker Compose file](docker-compose.yml) to bring up a Docker instance of Plex with some test files mounted. A new Movies library can then be created to use CAGEnt as the Agent, and hopefully all the files will auto match or be matchable!

The compose file by default mounts an NFS directory, remove this as the comments indicate if you instead want to mount a local directory. I intend to replace this with dummy media files for testing if I can figure out a Plex friendly way to do this (see issue [#26](https://github.com/gordonjb/cagent/issues/26))
