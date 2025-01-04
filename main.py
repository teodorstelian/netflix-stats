from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
from utils import calculate_stats, calculate_stats_per_profile, create_visualizations

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Home route for uploading CSV and displaying overall stats
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

# Route for profile-specific statistics and visualizations
@app.route("/profile/<profile_name>", methods=["GET"])
def profile(profile_name):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], "ViewingActivity.csv")  # Replace with actual file path
    df = pd.read_csv(file_path)
    profile_df = df[df["Profile Name"] == profile_name]
    stats = calculate_stats(profile_df)
    visuals = create_visualizations(profile_df)
    return render_template("profile.html", profile_name=profile_name, stats=stats, visuals=visuals)

if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
