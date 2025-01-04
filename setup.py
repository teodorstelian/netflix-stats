from setuptools import setup, find_packages

setup(
    name="netflix-stats",
    version="0.1.0",
    description="A brief description of your project",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://yourprojecthomepage.example.com",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "flask",
        "plotly"
    ],
    extras_require={
        "dev": ["pytest", "black"],  # Optional dependencies for development
    },
    python_requires=">=3.8",  # Specifies compatible Python versions
)