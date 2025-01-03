from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# Helper function to calculate stats
def calculate_stats(file_name):
    try:
        # Read the CSV file
        df = pd.read_csv(file_name)

        # Ensure necessary columns exist in the CSV
        required_columns = ["Profile Name", "Start Time", "Duration", "Title", "Device Type", "Country"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

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

        # Most-watched movies
        top_movies = (
            movies.groupby("Title")["Duration (seconds)"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )

        # Return stats as a dictionary
        return {
            "total_watch_time": f"{hours} hours, {minutes} minutes, {seconds} seconds",
            "tv_watch_time": tv_watch_time,
            "movie_watch_time": movie_watch_time,
            "top_tv_shows": top_tv_shows.to_dict(orient="records"),
            "top_movies": top_movies.to_dict(orient="records"),
        }

    except Exception as e:
        return {"error": str(e)}

@app.route("/", methods=["GET", "POST"])
def home():
    stats = None
    error = None
    if request.method == "POST":
        file_name = request.form.get("file_name", "ViewingActivity.csv")
        stats = calculate_stats(file_name)
        if "error" in stats:
            error = stats["error"]
            stats = None
    return render_template("index.html", stats=stats, error=error)

if __name__ == "__main__":
    app.run(debug=True)
