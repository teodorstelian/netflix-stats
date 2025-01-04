from flask import Flask, render_template, request, redirect
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper function to convert seconds to HH:MM:SS format
def seconds_to_hms(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

# Helper function to calculate stats for a given DataFrame
def calculate_stats(df):
    # Convert "Duration" to seconds
    def duration_to_seconds(duration):
        parts = duration.split(":")
        if len(parts) == 3:  # Format HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:  # Format MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return 0  # Invalid or empty duration

    df["Duration (seconds)"] = df["Duration"].apply(duration_to_seconds)

    # Extract main TV show title
    def extract_main_title(title):
        return title.split(":")[0] if "Episode" in title else title

    df["Main Title"] = df["Title"].apply(extract_main_title)

    # Separate TV shows and movies
    df["Category"] = df["Title"].apply(lambda x: "TV Show" if "Episode" in x else "Movie")

    # Stats for TV shows
    tv_shows = df[df["Category"] == "TV Show"]
    tv_shows_grouped = tv_shows.groupby("Main Title")["Duration (seconds)"].sum().reset_index()
    tv_shows_grouped["Duration"] = tv_shows_grouped["Duration (seconds)"].apply(seconds_to_hms)

    # Stats for Movies
    movies = df[df["Category"] == "Movie"]
    movies_grouped = movies.groupby("Title")["Duration (seconds)"].sum().reset_index()
    movies_grouped["Duration"] = movies_grouped["Duration (seconds)"].apply(seconds_to_hms)

    # Total watch time
    total_watch_time = df["Duration (seconds)"].sum()
    hours, remainder = divmod(total_watch_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Most-watched TV shows
    top_tv_shows = tv_shows_grouped.sort_values(by="Duration (seconds)", ascending=False).head(10).to_dict(orient="records")

    # Most-watched movies
    top_movies = movies_grouped.sort_values(by="Duration (seconds)", ascending=False).head(10).to_dict(orient="records")

    # Most-used devices
    top_devices = (
        df.groupby("Device Type")["Duration (seconds)"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .reset_index()
    )
    top_devices["Duration"] = top_devices["Duration (seconds)"].apply(seconds_to_hms)

    # Return stats as a dictionary
    return {
        "total_watch_time": f"{hours} hours, {minutes} minutes, {seconds} seconds",
        "tv_watch_time": seconds_to_hms(tv_shows["Duration (seconds)"].sum()),
        "movie_watch_time": seconds_to_hms(movies["Duration (seconds)"].sum()),
        "top_tv_shows": top_tv_shows,
        "top_movies": top_movies,
        "top_devices": top_devices.to_dict(orient="records"),
    }

# Function to calculate stats for each profile
def calculate_stats_per_profile(df):
    profiles = df["Profile Name"].unique()
    profile_stats = {}
    for profile in profiles:
        profile_df = df[df["Profile Name"] == profile]
        profile_stats[profile] = calculate_stats(profile_df)
    return profile_stats

# Function to create visualizations
def create_visualizations(df):
    visuals = {}

    # Total watch time per profile
    total_watch_time_per_profile = df.groupby("Profile Name")["Duration (seconds)"].sum().reset_index()
    total_watch_time_per_profile["Duration"] = total_watch_time_per_profile["Duration (seconds)"].apply(seconds_to_hms)
    fig1 = px.bar(total_watch_time_per_profile, x="Profile Name", y="Duration (seconds)", title="Total Watch Time per Profile")
    visuals["total_watch_time_per_profile"] = pio.to_html(fig1, full_html=False)

    # Most-watched TV shows
    tv_shows = df[df["Category"] == "TV Show"]
    top_tv_shows = tv_shows.groupby("Main Title")["Duration (seconds)"].sum().reset_index().sort_values(by="Duration (seconds)", ascending=False).head(10)
    top_tv_shows["Duration"] = top_tv_shows["Duration (seconds)"].apply(seconds_to_hms)
    fig2 = px.bar(top_tv_shows, x="Main Title", y="Duration (seconds)", title="Top 10 Most-Watched TV Shows")
    visuals["top_tv_shows"] = pio.to_html(fig2, full_html=False)

    # Most-watched Movies
    movies = df[df["Category"] == "Movie"]
    top_movies = movies.groupby("Title")["Duration (seconds)"].sum().reset_index().sort_values(by="Duration (seconds)", ascending=False).head(10)
    top_movies["Duration"] = top_movies["Duration (seconds)"].apply(seconds_to_hms)
    fig3 = px.bar(top_movies, x="Title", y="Duration (seconds)", title="Top 10 Most-Watched Movies")
    visuals["top_movies"] = pio.to_html(fig3, full_html=False)

    # Most-used devices
    top_devices = df.groupby("Device Type")["Duration (seconds)"].sum().reset_index().sort_values(by="Duration (seconds)", ascending=False).head(5)
    top_devices["Duration"] = top_devices["Duration (seconds)"].apply(seconds_to_hms)
    fig4 = px.pie(top_devices, names="Device Type", values="Duration (seconds)", title="Top 5 Most-Used Devices")
    visuals["top_devices"] = pio.to_html(fig4, full_html=False)

    return visuals

@app.route("/", methods=["GET", "POST"])
def home():
    stats = None
    profile_stats = None
    visuals = None
    error = None
    if request.method == "POST":
        if 'file' not in request.files:
            error = "No file part"
        file = request.files['file']
        if file.filename == '':
            error = "No selected file"
        if file and file.filename.endswith('.csv'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            try:
                df = pd.read_csv(file_path)
                stats = calculate_stats(df)
                profile_stats = calculate_stats_per_profile(df)
                visuals = create_visualizations(df)
            except Exception as e:
                error = str(e)
    return render_template("index.html", stats=stats, profile_stats=profile_stats, visuals=visuals, error=error)

if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
