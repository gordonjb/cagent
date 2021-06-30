import os, yaml

def ffmpeg(path, time):
    """If the provided path does not exist, uses `os.system` to call ffmpeg and create a 30fps, 
    720p video of {time} seconds, using a test pattern visual.

    """
    if not os.path.exists(path):
        print("Adding \"{path}\" w/ t= {time}".format(path=path, time=time))
        os.system("ffmpeg -f lavfi -i testsrc=duration={time}:size=1280x720:rate=30 \"{path}\"".format(path=path, time=time))
    else:
        print("{path} exists, skipping...".format(path=path))

# Main script starts

# Load YAML config file
config = yaml.safe_load(open("./test/test-files.yml"))

# Create the library root directory if it does not exist
directory = ".movies"
if not os.path.exists(directory):
    os.mkdir(directory)

# Set the starting duration for created files. The time is incremented in the loop
# to avoid Plex thinking files are duplicates and linking them together.
time = 100

# Iterate over each 'events' item. If they don't exist, create a folder with the item text
# and a video file with the same name and '.mkv' extension in that folder.
for event in config['events']:
    event_folder = os.path.join(directory, event)
    if not os.path.exists(event_folder):
        os.mkdir(event_folder)
    event_file = os.path.join(event_folder, event + ".mkv")
    ffmpeg(event_file, time)
    time = time + 5

# Iterate over each 'matches' item. If they don't exist, create a video file with the
# item name in the root library folder.
for match in config['matches']:
    match_file = os.path.join(directory, match)
    ffmpeg(match_file, time)
    time = time + 5