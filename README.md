# Plex Auto Genres
This is a third-party docker container to run the plex-auto-genres script (https://github.com/ShaneIsrael/plex-auto-genres) every day at 1AM UTC. The script has been modified to run without any input and log fetch results to a specific folder (that can be mounted) instead of the working directory.

Link to DockerHub : https://hub.docker.com/r/frank2312/plex-auto-genres

## How to Use
- Create the container. You can use the `docker-compose.yml` file as a template.
  - There are 2 ways to connect to your server : using your credentials and server name, or using an existing token and your server's URL.
    |Variable|Authentication method|Value|
    |---|---|---|
    |PLEX_USERNAME|Username and password|Your Plex Username|
    |PLEX_PASSWORD|Username and password|Your Plex Password|
    |PLEX_SERVER_NAME|Username and password|Your Plex Server Name|
    |PLEX_BASE_URL|Token|Your Plex Server base URL|
    |PLEX_TOKEN|Token|Your Plex Token|
    |TMDB_API_KEY|Both|Your the movie database api key (not required for anime library tagging)|
- Volume mount the `/config` folder that will contain the libraries for which you want the collections generated.
- (Optional) Volume mount the `/logs` folder that will contain the log files. The files can still be accessed by connecting to the container if it is not mounted.
  - Titles in the log files will not be re-processed. You must delete the log files to start a fresh run.
- Run the container once to generate the initial config file.
- Edit the generated config file (`libraries.txt`). 
    - Supported types :
        - standard-tv
        - standard-movie
        - anime
- Run manully (see [Manual run](#Manuel-run)) to check if it works or wait for the next automatic run.

## Manual run
You can start a manual run by connecting to the container's terminal and running the command
```
/generate-collections.sh
```
