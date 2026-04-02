import os
import pandas as pd
import plotly.express as px
import plotly.io as pio

from settings import COLLECTIONS, NUMBER_RANKING


def seconds_to_hms(seconds):
    seconds = int(seconds or 0)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def seconds_to_hours(seconds):
    return (seconds or 0) / 3600


def duration_to_seconds(duration):
    if pd.isna(duration):
        return 0

    parts = str(duration).strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        return 0

    return 0


def extract_main_title(title):
    title = str(title).strip()
    parts = [part.strip() for part in title.split(":")]

    for i, part in enumerate(parts):
        if "Season" in part or "Limited Series" in part:
            return ":".join(parts[:i]).strip()

    return parts[0].strip() if parts else title


def create_collection(title):
    title = str(title)
    for collection, titles in COLLECTIONS.items():
        if any(t in title for t in titles):
            return collection
    return None


def classify_category(title):
    title = str(title)
    return "TV Show" if "Episode" in title else "Movie"


def is_supplemental_row(row):
    supplemental = str(row.get("Supplemental Video Type", "")).strip().upper()
    title = str(row.get("Title", "")).strip().lower()

    excluded_types = {"HOOK", "TEASER_TRAILER"}
    excluded_terms = ["hook", "trailer", "teaser", "clip"]

    if supplemental in excluded_types:
        return True

    if any(term in title for term in excluded_terms):
        return True

    return False


def prepare_dataframe(df):
    df = df.copy()

    df["Duration (seconds)"] = df["Duration"].apply(duration_to_seconds)
    df["Main Title"] = df["Title"].apply(extract_main_title)
    df["Collection"] = df["Title"].apply(create_collection)
    df["Category"] = df["Title"].apply(classify_category)
    df["Start Time Parsed"] = pd.to_datetime(df["Start Time"], dayfirst=True, errors="coerce")

    return df


def calculate_stats(df):
    df = prepare_dataframe(df)

    tv_shows = df[df["Category"] == "TV Show"].copy()
    tv_shows_grouped = (
        tv_shows.groupby("Main Title")["Duration (seconds)"]
        .sum()
        .reset_index()
    )
    tv_shows_grouped["Duration"] = tv_shows_grouped["Duration (seconds)"].apply(seconds_to_hms)
    tv_shows_grouped["Rank"] = (
        tv_shows_grouped["Duration (seconds)"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    movies = df[df["Category"] == "Movie"].copy()
    movies_grouped = (
        movies.groupby("Title")["Duration (seconds)"]
        .sum()
        .reset_index()
    )
    movies_grouped["Duration"] = movies_grouped["Duration (seconds)"].apply(seconds_to_hms)
    movies_grouped["Rank"] = (
        movies_grouped["Duration (seconds)"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    collections = df[df["Collection"].notna()].copy()
    collections_grouped = (
        collections.groupby("Collection")["Duration (seconds)"]
        .sum()
        .reset_index()
    )
    collections_grouped["Duration"] = collections_grouped["Duration (seconds)"].apply(seconds_to_hms)
    collections_grouped["Rank"] = (
        collections_grouped["Duration (seconds)"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    total_watch_time = int(df["Duration (seconds)"].sum())
    hours, remainder = divmod(total_watch_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    top_tv_shows = (
        tv_shows_grouped.sort_values(by="Rank")
        .head(NUMBER_RANKING)
        .to_dict(orient="records")
    )

    top_movies = (
        movies_grouped.sort_values(by="Rank")
        .head(NUMBER_RANKING)
        .to_dict(orient="records")
    )

    top_devices = (
        df.groupby("Device Type")["Duration (seconds)"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .reset_index()
    )
    top_devices["Duration"] = top_devices["Duration (seconds)"].apply(seconds_to_hms)

    top_collections = (
        collections_grouped.sort_values(by="Rank")
        .head(NUMBER_RANKING)
        .to_dict(orient="records")
    )

    return {
        "total_watch_time": f"{hours} hours, {minutes} minutes, {seconds} seconds",
        "tv_watch_time": seconds_to_hms(tv_shows["Duration (seconds)"].sum()),
        "movie_watch_time": seconds_to_hms(movies["Duration (seconds)"].sum()),
        "top_tv_shows": top_tv_shows,
        "top_movies": top_movies,
        "top_devices": top_devices.to_dict(orient="records"),
        "top_collections": top_collections,
    }


def calculate_stats_per_profile(df):
    df = prepare_dataframe(df)

    profiles = df["Profile Name"].dropna().unique()
    profile_stats = {}

    for profile in profiles:
        profile_df = df[df["Profile Name"] == profile].copy()
        profile_stats[profile] = calculate_stats(profile_df)

    return profile_stats


def calculate_continue_watching(df):
    df = prepare_dataframe(df)

    tv_df = df[df["Category"] == "TV Show"].copy()
    tv_df = tv_df[~tv_df.apply(is_supplemental_row, axis=1)].copy()

    if tv_df.empty:
        return {}

    tv_df["Has Real Latest Bookmark"] = tv_df["Latest Bookmark"].apply(
        lambda x: isinstance(x, str) and x.strip() != "" and x != "Not latest view"
    )

    continue_data = {}

    for profile in tv_df["Profile Name"].dropna().unique():
        profile_df = tv_df[tv_df["Profile Name"] == profile].copy()

        profile_df = profile_df.sort_values(
            by=["Main Title", "Has Real Latest Bookmark", "Start Time Parsed"],
            ascending=[True, False, False]
        )

        latest_per_show = profile_df.groupby("Main Title", as_index=False).first()

        latest_per_show["Progress"] = latest_per_show.apply(
            lambda row: row["Latest Bookmark"]
            if row["Has Real Latest Bookmark"]
            else row["Bookmark"],
            axis=1
        )

        latest_per_show = latest_per_show.sort_values(
            by="Start Time Parsed",
            ascending=False
        )

        continue_data[profile] = latest_per_show[
            ["Main Title", "Title", "Start Time", "Progress", "Device Type"]
        ].rename(
            columns={
                "Title": "Last Title",
                "Start Time": "Last Watch Time"
            }
        ).to_dict(orient="records")

    return continue_data


def create_visualizations(df):
    df = prepare_dataframe(df)
    visuals = {}

    total_watch_time_per_profile = (
        df.groupby("Profile Name")["Duration (seconds)"]
        .sum()
        .reset_index()
    )
    total_watch_time_per_profile["Duration (hours)"] = total_watch_time_per_profile["Duration (seconds)"].apply(seconds_to_hours)
    fig1 = px.bar(
        total_watch_time_per_profile,
        x="Profile Name",
        y="Duration (hours)",
        title="Total Watch Time per Profile (in hours)"
    )
    visuals["total_watch_time_per_profile"] = pio.to_html(fig1, full_html=False)

    tv_shows = df[df["Category"] == "TV Show"].copy()
    top_tv_shows = (
        tv_shows.groupby("Main Title")["Duration (seconds)"]
        .sum()
        .reset_index()
        .sort_values(by="Duration (seconds)", ascending=False)
        .head(10)
    )
    top_tv_shows["Duration (hours)"] = top_tv_shows["Duration (seconds)"].apply(seconds_to_hours)
    fig2 = px.bar(
        top_tv_shows,
        x="Main Title",
        y="Duration (hours)",
        title="Top 10 Most-Watched TV Shows (in hours)"
    )
    visuals["top_tv_shows"] = pio.to_html(fig2, full_html=False)

    movies = df[df["Category"] == "Movie"].copy()
    top_movies = (
        movies.groupby("Title")["Duration (seconds)"]
        .sum()
        .reset_index()
        .sort_values(by="Duration (seconds)", ascending=False)
        .head(10)
    )
    top_movies["Duration (hours)"] = top_movies["Duration (seconds)"].apply(seconds_to_hours)
    fig3 = px.bar(
        top_movies,
        x="Title",
        y="Duration (hours)",
        title="Top 10 Most-Watched Movies (in hours)"
    )
    visuals["top_movies"] = pio.to_html(fig3, full_html=False)

    top_devices = (
        df.groupby("Device Type")["Duration (seconds)"]
        .sum()
        .reset_index()
        .sort_values(by="Duration (seconds)", ascending=False)
        .head(5)
    )
    top_devices["Duration (hours)"] = top_devices["Duration (seconds)"].apply(seconds_to_hours)
    fig4 = px.pie(
        top_devices,
        names="Device Type",
        values="Duration (hours)",
        title="Top 5 Most-Used Devices (in hours)"
    )
    visuals["top_devices"] = pio.to_html(fig4, full_html=False)

    collections = df[df["Collection"].notna()].copy()
    top_collections = (
        collections.groupby("Collection")["Duration (seconds)"]
        .sum()
        .reset_index()
        .sort_values(by="Duration (seconds)", ascending=False)
        .head(10)
    )
    top_collections["Duration (hours)"] = top_collections["Duration (seconds)"].apply(seconds_to_hours)
    fig5 = px.bar(
        top_collections,
        x="Collection",
        y="Duration (hours)",
        title="Top 10 Collections (in hours)"
    )
    visuals["top_collections"] = pio.to_html(fig5, full_html=False)

    return visuals


def export_tv_shows_and_movies_to_txt(df, output_file="tv_shows_movies.txt"):
    df = prepare_dataframe(df)

    exclusion_terms = ["hook", "trailer", "season", "teaser", "clip"]

    def filter_entries(entries):
        return {
            entry for entry in entries
            if not any(term.lower() in str(entry).lower() for term in exclusion_terms)
        }

    tv_shows = set(df[df["Category"] == "TV Show"]["Main Title"].dropna().unique())
    movies = set(df[df["Category"] == "Movie"]["Title"].dropna().unique())

    tv_shows = filter_entries(tv_shows)
    movies = filter_entries(movies)

    existing_tv_shows = set()
    existing_movies = set()

    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        is_tv_show_section = True
        for line in lines:
            line = line.strip()
            if line == "Movies:":
                is_tv_show_section = False
            elif line.startswith("- "):
                if is_tv_show_section:
                    existing_tv_shows.add(line[2:])
                else:
                    existing_movies.add(line[2:])

    all_tv_shows = existing_tv_shows.union(tv_shows)
    all_movies = existing_movies.union(movies)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("TV Shows:\n")
        f.writelines(f"- {tv_show}\n" for tv_show in sorted(all_tv_shows))

        f.write("\nMovies:\n")
        f.writelines(f"- {movie}\n" for movie in sorted(all_movies))

    print(f"TV shows and movies updated in {output_file}")