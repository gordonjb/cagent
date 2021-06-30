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

**NOTE**: You need to use a 2.7.x version of Python to fetch these dependencies, otherwise pip will fetch 3.x versions of the dependencies that Plex will not understand. You can use [pyenv](https://github.com/pyenv/pyenv) to manage and install specific versions of Python.

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

To test the agent, I use the included [Docker Compose file](test/docker-compose.yml) to bring up a Docker instance of Plex with some test files mounted. A new Movies library can then be created to use CAGEnt as the Agent, and automatching and manual matching can be tested using these test files.

The compose file by default mounts a `.movies` directory. This directory is generated and populated with test files by [test/populate-media.py](test/populate-media.py). The script looks at the values in [test/test-files.yml](test/test-files.yml) and generates test files and folders using ffmpeg. If you have your own files you want to test against, you can edit the mount folder in the compose file, or add entries to `test-files.yml`.

To generate the test files:

- **Requirement**: Install ffmpeg and have it available on the path.
- **Requirement**: Have pyyaml available. If not installed, run `pip install pyyaml`.
- From the root of this project, run `python ./test/populate-media.py`.

Once your test files are prepared, from the `test` directory run `docker-compose up -d` to bring up Plex. Go to [localhost:32400/web/index.html](http://localhost:32400/web/index.html) and run through the server setup steps to begin testing.
