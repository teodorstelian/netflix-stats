import pandas as pd
import plotly.express as px
import plotly.io as pio
import os

from settings import COLLECTIONS, NUMBER_RANKING


# Utility functions
def seconds_to_hms(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def seconds_to_hours(seconds):
    return seconds / 3600

def calculate_stats(df):
    def duration_to_seconds(duration):
        parts = duration.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return 0

    df["Duration (seconds)"] = df["Duration"].apply(duration_to_seconds)

    def extract_main_title(title):
        parts = title.split(":")
        for i, part in enumerate(parts):
            if "Season" in part:
                return ":".join(parts[:i]).strip()
        return parts[0]

    def create_collection(title):
        for collection, titles in COLLECTIONS.items():
            if any(t in title for t in titles):
                return collection
        return None

    df["Main Title"] = df["Title"].apply(extract_main_title)
    df["Collection"] = df["Title"].apply(create_collection)

    df["Category"] = df["Title"].apply(lambda x: "TV Show" if "Episode" in x else "Movie")

    tv_shows = df[df["Category"] == "TV Show"]
    tv_shows_grouped = tv_shows.groupby("Main Title")["Duration (seconds)"].sum().reset_index()
    tv_shows_grouped["Duration"] = tv_shows_grouped["Duration (seconds)"].apply(seconds_to_hms)
    tv_shows_grouped["Rank"] = tv_shows_grouped["Duration (seconds)"].rank(method="min", ascending=False).astype(int)

    movies = df[df["Category"] == "Movie"]
    movies_grouped = movies.groupby("Title")["Duration (seconds)"].sum().reset_index()
    movies_grouped["Duration"] = movies_grouped["Duration (seconds)"].apply(seconds_to_hms)
    movies_grouped["Rank"] = movies_grouped["Duration (seconds)"].rank(method="min", ascending=False).astype(int)

    collections = df[df["Collection"].notna()]
    collections_grouped = collections.groupby("Collection")["Duration (seconds)"].sum().reset_index()
    collections_grouped["Duration"] = collections_grouped["Duration (seconds)"].apply(seconds_to_hms)
    collections_grouped["Rank"] = collections_grouped["Duration (seconds)"].rank(method="min", ascending=False).astype(int)

    total_watch_time = df["Duration (seconds)"].sum()
    hours, remainder = divmod(total_watch_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    top_tv_shows = tv_shows_grouped.sort_values(by="Rank").head(NUMBER_RANKING).to_dict(orient="records")
    top_movies = movies_grouped.sort_values(by="Rank").head(NUMBER_RANKING).to_dict(orient="records")

    top_devices = df.groupby("Device Type")["Duration (seconds)"].sum().sort_values(ascending=False).head(5).reset_index()
    top_devices["Duration"] = top_devices["Duration (seconds)"].apply(seconds_to_hms)

    top_collections = collections_grouped.sort_values(by="Rank").head(NUMBER_RANKING).to_dict(orient="records")

    export_tv_shows_and_movies_to_txt(df)

    return {
        "total_watch_time": f"{hours} hours, {minutes} minutes, {seconds} seconds",
        "tv_watch_time": seconds_to_hms(tv_shows["Duration (seconds)"].sum()),
        "movie_watch_time": seconds_to_hms(movies["Duration (seconds)"].sum()),
        "top_tv_shows": top_tv_shows,
        "top_movies": top_movies,
        "top_devices": top_devices.to_dict(orient="records"),
        "top_collections": top_collections,
    }
import os


def export_tv_shows_and_movies_to_txt(df, output_file="tv_shows_movies.txt"):
    # Terms to exclude
    exclusion_terms = ["hook", "trailer", "season", "teaser", "clip"]

    # Helper function to filter out unwanted entries
    def filter_entries(entries):
        return {entry for entry in entries
                if not any(term.lower() in entry.lower() for term in exclusion_terms)}

    # Extract TV shows
    tv_shows = set(df[df["Category"] == "TV Show"]["Main Title"].unique())
    # Extract Movies
    movies = set(df[df["Category"] == "Movie"]["Title"].unique())

    # Filter out entries containing exclusion terms
    tv_shows = filter_entries(tv_shows)
    movies = filter_entries(movies)

    # Prepare to merge with existing file content
    existing_tv_shows = set()
    existing_movies = set()

    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        is_tv_show_section = True  # To identify whether we are parsing TV Shows or Movies
        for line in lines:
            line = line.strip()
            if line == "Movies:":
                is_tv_show_section = False
            elif line.startswith("- "):  # Entries start with "- "
                if is_tv_show_section:
                    existing_tv_shows.add(line[2:])  # Add to TV shows
                else:
                    existing_movies.add(line[2:])  # Add to Movies

    # Merge existing and new entries
    all_tv_shows = existing_tv_shows.union(tv_shows)
    all_movies = existing_movies.union(movies)

    # Write the updated list back to the file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("TV Shows:\n")
        f.writelines(f"- {tv_show}\n" for tv_show in sorted(all_tv_shows))

        f.write("\nMovies:\n")
        f.writelines(f"- {movie}\n" for movie in sorted(all_movies))

    print(f"TV shows and movies updated (filtered unwanted entries) in {output_file}")


def calculate_stats_per_profile(df):
    profiles = df["Profile Name"].unique()
    profile_stats = {}
    for profile in profiles:
        profile_df = df[df["Profile Name"] == profile]
        profile_stats[profile] = calculate_stats(profile_df)
    return profile_stats

def create_visualizations(df):
    visuals = {}

    total_watch_time_per_profile = df.groupby("Profile Name")["Duration (seconds)"].sum().reset_index()
    total_watch_time_per_profile["Duration (hours)"] = total_watch_time_per_profile["Duration (seconds)"].apply(seconds_to_hours)
    fig1 = px.bar(total_watch_time_per_profile, x="Profile Name", y="Duration (hours)", title="Total Watch Time per Profile (in hours)")
    visuals["total_watch_time_per_profile"] = pio.to_html(fig1, full_html=False)

    tv_shows = df[df["Category"] == "TV Show"]
    top_tv_shows = tv_shows.groupby("Main Title")["Duration (seconds)"].sum().reset_index().sort_values(by="Duration (seconds)", ascending=False).head(10)
    top_tv_shows["Duration (hours)"] = top_tv_shows["Duration (seconds)"].apply(seconds_to_hours)
    fig2 = px.bar(top_tv_shows, x="Main Title", y="Duration (hours)", title="Top 10 Most-Watched TV Shows (in hours)")
    visuals["top_tv_shows"] = pio.to_html(fig2, full_html=False)

    movies = df[df["Category"] == "Movie"]
    top_movies = movies.groupby("Title")["Duration (seconds)"].sum().reset_index().sort_values(by="Duration (seconds)", ascending=False).head(10)
    top_movies["Duration (hours)"] = top_movies["Duration (seconds)"].apply(seconds_to_hours)
    fig3 = px.bar(top_movies, x="Title", y="Duration (hours)", title="Top 10 Most-Watched Movies (in hours)")
    visuals["top_movies"] = pio.to_html(fig3, full_html=False)

    top_devices = df.groupby("Device Type")["Duration (seconds)"].sum().reset_index().sort_values(by="Duration (seconds)", ascending=False).head(5)
    top_devices["Duration (hours)"] = top_devices["Duration (seconds)"].apply(seconds_to_hours)
    fig4 = px.pie(top_devices, names="Device Type", values="Duration (hours)", title="Top 5 Most-Used Devices (in hours)")
    visuals["top_devices"] = pio.to_html(fig4, full_html=False)

    collections = df[df["Collection"].notna()]
    top_collections = collections.groupby("Collection")["Duration (seconds)"].sum().reset_index().sort_values(by="Duration (seconds)", ascending=False).head(10)
    top_collections["Duration (hours)"] = top_collections["Duration (seconds)"].apply(seconds_to_hours)
    fig5 = px.bar(top_collections, x="Collection", y="Duration (hours)", title="Top 10 Collections (in hours)")
    visuals["top_collections"] = pio.to_html(fig5, full_html=False)

    return visuals
