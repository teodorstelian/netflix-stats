import pandas as pd
import plotly.express as px
import plotly.io as pio

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

    df["Main Title"] = df["Title"].apply(extract_main_title)

    df["Category"] = df["Title"].apply(lambda x: "TV Show" if "Episode" in x else "Movie")

    tv_shows = df[df["Category"] == "TV Show"]
    tv_shows_grouped = tv_shows.groupby("Main Title")["Duration (seconds)"].sum().reset_index()
    tv_shows_grouped["Duration"] = tv_shows_grouped["Duration (seconds)"].apply(seconds_to_hms)

    movies = df[df["Category"] == "Movie"]
    movies_grouped = movies.groupby("Title")["Duration (seconds)"].sum().reset_index()
    movies_grouped["Duration"] = movies_grouped["Duration (seconds)"].apply(seconds_to_hms)

    total_watch_time = df["Duration (seconds)"].sum()
    hours, remainder = divmod(total_watch_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    top_tv_shows = tv_shows_grouped.sort_values(by="Duration (seconds)", ascending=False).head(10).to_dict(orient="records")
    top_movies = movies_grouped.sort_values(by="Duration (seconds)", ascending=False).head(10).to_dict(orient="records")

    top_devices = df.groupby("Device Type")["Duration (seconds)"].sum().sort_values(ascending=False).head(5).reset_index()
    top_devices["Duration"] = top_devices["Duration (seconds)"].apply(seconds_to_hms)

    return {
        "total_watch_time": f"{hours} hours, {minutes} minutes, {seconds} seconds",
        "tv_watch_time": seconds_to_hms(tv_shows["Duration (seconds)"].sum()),
        "movie_watch_time": seconds_to_hms(movies["Duration (seconds)"].sum()),
        "top_tv_shows": top_tv_shows,
        "top_movies": top_movies,
        "top_devices": top_devices.to_dict(orient="records"),
    }

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

    return visuals
