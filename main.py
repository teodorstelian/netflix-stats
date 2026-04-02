from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
from utils import (
    calculate_stats,
    calculate_stats_per_profile,
    create_visualizations,
    calculate_continue_watching,
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Function to list files in UPLOAD_FOLDER
def list_uploaded_files():
    return [f for f in os.listdir(UPLOAD_FOLDER) if
            os.path.isfile(os.path.join(UPLOAD_FOLDER, f)) and f.endswith('.csv')]


# Home route for uploading CSV and displaying available files
@app.route("/", methods=["GET", "POST"])
def home():
    error = None
    files = list_uploaded_files()

    if request.method == "POST":
        # Handle file selection from existing files
        selected_file = request.form.get("existing_file")
        if selected_file:
            return redirect(url_for('stats', filename=selected_file))
        else:
            # Handle file upload
            if 'file' not in request.files:
                error = "No file part"
            file = request.files['file']
            if file.filename == '':
                error = "No selected file"
            if file and file.filename.endswith('.csv'):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                return redirect(url_for('stats', filename=filename))

    return render_template("index.html", error=error, files=files)


# Route for viewing detailed statistics
@app.route("/stats/<filename>", methods=["GET"])
def stats(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df = pd.read_csv(file_path)

    stats = calculate_stats(df)
    profile_stats = calculate_stats_per_profile(df)
    continue_watching = calculate_continue_watching(df)

    return render_template(
        "stats.html",
        stats=stats,
        profile_stats=profile_stats,
        continue_watching=continue_watching,
        filename=filename
    )

# Route for viewing visualizations
@app.route("/visualizations/<filename>", methods=["GET"])
def visualizations(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df = pd.read_csv(file_path)
    # Ensure Duration (seconds) column is created by invoking calculate_stats first
    calculate_stats(df)
    visuals = create_visualizations(df)
    return render_template("visualizations.html", visuals=visuals, filename=filename)


# Route for profile-specific statistics and visualizations
@app.route("/profile/<profile_name>/<filename>", methods=["GET"])
def profile(profile_name, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df = pd.read_csv(file_path)
    profile_df = df[df["Profile Name"] == profile_name]
    stats = calculate_stats(profile_df)
    visuals = create_visualizations(profile_df)
    return render_template("profile.html", profile_name=profile_name, stats=stats, visuals=visuals)


if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
