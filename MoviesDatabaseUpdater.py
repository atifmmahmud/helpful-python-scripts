#region Imports
import os
import requests
import validators
import time
from notion_client import Client
from dotenv import load_dotenv
#endregion

#region Read data from .env
load_dotenv()
database_id = os.getenv("DATA_SOURCE_ID")
destination_id = os.getenv("DATA_DESTINATION_ID")
notion_key = os.getenv("NOTION_TOKEN")
file_upload_url = os.getenv("FILE_UPLOAD_URL")
omdb_key = os.getenv("OMDB_KEY")
#endregion

#region Get names of movies from source db
def get_movie_names(response):
    names = []
    for result in response["results"]:
        if (result["properties"]["Name"]["title"]):
            names.append(result["properties"]["Name"]["title"][0]["plain_text"])
    return names
#endregion

#region Set up file upload
def create_and_upload_file(url, filename):
    payload = {
        "filename" : filename,
        "content-type" : "image/jpeg"
    }

    response = requests.post(url, json=payload, headers={
        "Authorization": f"Bearer {notion_key}",
        "accept": "application/json",
        "content-type": "application/json",
        "Notion-Version": "2026-03-11"
    })

    if (response.status_code == 200):
        id = response.json()["id"]
    
    with open (filename, "rb") as f:
        files = {
            "file" : (filename, f, "image/jpeg")
        }
        sendurl = f"{url}{id}/send"
        response = requests.post(
            f"{url}{id}/send",
            headers={
                "Authorization": f"Bearer {notion_key}",
                "Notion-Version": "2026-03-11"
            },
            files=files
        )
    print(filename)
    print(response.json())
    return id
#endregion

#region Create row in database
def create_database_entry(name, year, languages, genres, directors, plot, runtime, imdbRating, metascore, awards, file_id):
    # Write to notion database
    notion.pages.create(
        parent={"data_source_id": destination_id},
            properties={
                "Name": {"title": [{"text": {"content": name}}]},
                "Year": {"select": {"name": year}},
                "Language": {"multi_select": languages},
                "Genre": {"multi_select": genres},
                "Director": {"multi_select": directors},
                "Synopsis": {"rich_text": [{"text": {"content": plot}}]},
                "Runtime": {"rich_text": [{"text": {"content": runtime}}]},
                "IMDB Rating": {"rich_text": [{"text": {"content": imdbRating}}]},
                "Metascore": {"rich_text": [{"text": {"content": metascore}}]},
                "Awards": {"rich_text": [{"text": {"content": awards}}]},
                "Poster": {"files": [{"file_upload": {"id": file_id}}]},
                "Script Updated" : {"checkbox" : True}
            })
#endregion

#region Get movie data for each movie from list of names
def retrieve_data(names):
    # Get movie data from TMDB using movie title
    # Populate the new database line by line
    for name in names:
        response = requests.get("http://www.omdbapi.com/?apikey={key}&t={title}&plot=short".format(key = omdb_key, title = name))
        movie_data = response.json()
        print(movie_data)

        if (movie_data["Response"] == "True"):
            name = movie_data["Title"]
            year = movie_data["Year"]
            language = movie_data["Language"]
            genre = movie_data["Genre"]
            director = movie_data["Director"]
            plot = movie_data["Plot"]
            runtime = movie_data["Runtime"]
            poster_url = movie_data["Poster"]
            imdb_id = movie_data["imdbID"]
            imdb_ratings = movie_data["imdbRating"]
            metascore = movie_data["Metascore"]
            awards = movie_data["Awards"]
            
            # Save poster image
            if (validators.url(poster_url)):
                poster_data = requests.get(poster_url)
                image_filename = "images/{poster}.jpg".format(poster=name + "_poster")
                with open(image_filename, "wb") as f:
                    f.write(poster_data.content)

            # Create multi-select compatible array from comma-separated list as string
            languages = [{"name" : l.strip()} for l in language.split(",")]
            genres = [{"name" : g.strip()} for g in genre.split(",")]
            directors = [{"name" : d.strip()} for d in director.split(",")]

            poster_file_id = create_and_upload_file(file_upload_url, image_filename)
            time.sleep(2)
            create_database_entry(name, year, languages, genres, directors, plot, runtime, imdb_ratings, metascore, awards, poster_file_id)
#endregion

notion = Client(auth=notion_key)

# Get list of names from the original database in notion
movie_entries = notion.data_sources.query(data_source_id = database_id)
print(movie_entries)
# names = get_movie_names(movie_entries)
# retrieve_data(names)
