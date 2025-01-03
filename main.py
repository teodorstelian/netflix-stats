from flask import Flask, render_template, request, redirect
import pandas as pd
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

    # Separate TV shows and movies
    df["Category"] = df["Title"].apply(lambda x: "TV Show" if "Episode" in x else "Movie")

    # Stats for TV shows
    tv_shows = df[df["Category"] == "TV Show"]
    tv_watch_time = tv_shows["Duration (seconds)"].sum()

    # Stats for Movies
    movies = df[df["Category"] == "Movie"]
    movie_watch_time = movies["Duration (seconds)"].sum()

    # Total watch time
    total_watch_time = df["Duration (seconds)"].sum()
    hours, remainder = divmod(total_watch_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Most-watched TV shows
    top_tv_shows = (
        tv_shows.groupby("Title")["Duration (seconds)"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_tv_shows["Duration"] = top_tv_shows["Duration (seconds)"].apply(seconds_to_hms)

    # Most-watched movies
    top_movies = (
        movies.groupby("Title")["Duration (seconds)"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_movies["Duration"] = top_movies["Duration (seconds)"].apply(seconds_to_hms)

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
        "tv_watch_time": seconds_to_hms(tv_watch_time),
        "movie_watch_time": seconds_to_hms(movie_watch_time),
        "top_tv_shows": top_tv_shows.to_dict(orient="records"),
        "top_movies": top_movies.to_dict(orient="records"),
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

@app.route("/", methods=["GET", "POST"])
def home():
    stats = None
    profile_stats = None
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
            except Exception as e:
                error = str(e)
    return render_template("index.html", stats=stats, profile_stats=profile_stats, error=error)

if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
