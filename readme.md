# 🎵 Clips Backend API - Complete Guide

A simple web service for managing and streaming short audio clips.

## 🌟 What This Project Does

Imagine you have a music library app where people can:
- Browse a list of short audio clips (like previews of songs)
- Play these clips by clicking on them
- See how many times each clip has been played
- Add new clips to the library

This project creates the "behind-the-scenes" part (called a backend) that makes all of this possible. It's like having a smart filing cabinet that can:
- Store information about audio clips
- Keep track of how popular each clip is
- Serve audio files when someone wants to listen
- Monitor how well everything is working

## 🎯 Project Overview for Non-Technical People

### What You'll See When It's Running
1. **A Web API** - A service that responds to requests (like "show me all clips" or "play clip #3")
2. **A Database** - Where all the clip information is stored (titles, descriptions, play counts)
3. **A Monitoring Dashboard** - Pretty graphs showing how busy your service is
4. **Audio Playback** - You can actually listen to the clips through your web browser

### Real-World Example
Think of it like a digital jukebox:
- The **database** is like the catalog of all available songs
- The **API** is like the buttons you press to select songs
- The **monitoring** is like the screen showing which songs are most popular
- The **audio streaming** is the actual music coming out of the speakers

## 📁 What's In This Project (File by File)

### 📋 Main Application Files

**`app/main.py`** - The Heart of the Application
- This is like the main control center
- It handles all requests (like "show me clips" or "play a clip")
- Think of it as the receptionist who directs people to the right department

**`app/models.py`** - Database Blueprint
- Describes what information we store about each clip (title, genre, play count, etc.)
- Like a form template that defines what fields each clip record must have

**`app/database.py`** - Database Connection
- Handles talking to the database (where we store all our data)
- Like a telephone line connecting our app to the filing cabinet

**`app/schemas.py`** - Data Validation Rules
- Makes sure incoming data is correct (like checking if a phone number has the right format)
- Prevents bad data from getting into our system

**`app/crud.py`** - Database Operations
- Contains the actual commands for database actions (create, read, update, delete)
- Like having specific procedures for filing, finding, and updating records

**`app/config.py`** - Settings and Configuration
- Stores important settings like database passwords and secret keys
- Like a settings file for the entire application

### 🗃️ Data and Setup Files

**`seed_data.py`** - Sample Data Creator
- Creates 6 example audio clips when you first set up the project
- Like pre-filling a new library with some starter books

**`requirements.txt`** - Software Dependencies List
- Lists all the software libraries this project needs to work
- Like an ingredients list for a recipe

**`.env`** - Secret Configuration (You Create This)
- Stores sensitive information like passwords
- Never shared publicly (like your personal diary)

### 🐳 Docker Files (For Easy Setup)

**`docker-compose.yml`** - Complete Service Setup
- Automatically sets up the entire system with one command
- Like a recipe that prepares a complete meal with all side dishes

**`Dockerfile`** - Application Container Blueprint
- Instructions for packaging the app so it runs the same everywhere
- Like a detailed shipping box that ensures your product arrives intact

### 🧪 Testing Files

**`simple_test.py`** - Easy Testing Script
- Automatically tests if everything is working correctly
- Like a health checkup for your application

**`tests/`** folder - Professional Testing Suite
- More detailed tests that developers use
- Like a comprehensive medical exam vs. a basic checkup

### 📊 Monitoring Files

**`prometheus.yml`** - Metrics Collection Setup
- Configures what data to collect about your app's performance
- Like setting up sensors to monitor your car's engine

**`grafana/dashboard.json`** - Pretty Graphs Configuration
- Creates beautiful charts and graphs from your app's data
- Like turning spreadsheet data into colorful charts

### 🚀 Deployment Files

**`railway.json`**, **`render.yaml`**, **`vercel.json`** - Deployment Configurations
- Instructions for different hosting services to run your app online
- Like address labels for shipping your app to different delivery services

**`terraform/`** folder - Cloud Infrastructure Setup
- Professional-grade cloud setup (advanced users only)
- Like hiring an architect to design your app's hosting infrastructure

## 🚀 How to Run This Project

### Option 1: Super Easy Way (Using Docker)

**What You Need:**
- A computer with internet connection
- Docker Desktop installed ([download here](https://www.docker.com/products/docker-desktop/))

**Steps:**
1. **Download the project** to your computer
2. **Open a terminal/command prompt** in the project folder
3. **Run one command:**
   ```bash
   docker-compose up --build -d
   ```
4. **Wait 2 minutes** for everything to start up
5. **Load sample data:**
   ```bash
   docker-compose exec api python seed_data.py
   ```

**That's it!** Your app is now running.

### Option 2: Manual Setup (For Developers)

**What You Need:**
- Python 3.11 or higher
- PostgreSQL database
- More technical knowledge

**Steps:**
1. Install Python dependencies: `pip install -r requirements.txt`
2. Set up PostgreSQL database
3. Configure environment variables in `.env` file
4. Run database setup: `python seed_data.py`
5. Start the application: `uvicorn app.main:app --reload`

## 🌐 How to Use Your Running Application

### 1. View the API Documentation
- Open your web browser
- Go to: `http://localhost:8000/docs`
- You'll see a beautiful interface showing all available features

### 2. Test the Basic Features
- **See all clips:** Visit `http://localhost:8000/clips`
- **Play a clip:** Visit `http://localhost:8000/clips/1/stream`
- **Check play stats:** Visit `http://localhost:8000/clips/1/stats`

### 3. View the Monitoring Dashboard
- Open: `http://localhost:3000`
- Login with username: `admin`, password: `admin`
- See real-time graphs of your app's performance

### 4. Play Audio Clips
Create an HTML file called `player.html` (provided in the project) and open it in your browser for a user-friendly audio player interface.

## 🎵 What Sample Data You'll Get

When you run the setup, you'll automatically get 6 sample audio clips:

1. **Ocean Waves** (Ambient, 30 seconds) - Relaxing ocean sounds
2. **Urban Beat** (Electronic, 45 seconds) - Modern city vibes
3. **Acoustic Guitar** (Acoustic, 60 seconds) - Gentle guitar melody
4. **Rain Forest** (Ambient, 40 seconds) - Nature sounds
5. **Synthwave Dream** (Electronic, 55 seconds) - Retro futuristic music
6. **Jazz Piano** (Jazz, 35 seconds) - Smooth piano improvisation

Each clip starts with 0 plays, and the count increases every time someone streams it.

## 📊 Understanding the Monitoring Dashboard

### What You'll See in Grafana (the monitoring tool):

**"Total API Requests"** - How many people have used your app
- Like counting visitors to your store

**"Response Time"** - How fast your app responds
- Like measuring how quickly a cashier serves customers

**"Stream Count by Clip"** - Which clips are most popular
- Like seeing which books are checked out most from a library

**"Request Rate Over Time"** - How busy your app is throughout the day
- Like tracking customer traffic patterns in a store

**"Error Rate"** - How often things go wrong
- Like tracking customer complaints

### Manual Testing (Using Your Browser)
1. **Check if it's working:** `http://localhost:8000/health`
2. **See all clips:** `http://localhost:8000/clips`
3. **Play a clip:** `http://localhost:8000/clips/1/stream`
4. **Check how many times it was played:** `http://localhost:8000/clips/1/stats`

## 🔧 Troubleshooting Common Issues

### "Nothing is working!"
- **Check if Docker is running** - Look for the Docker whale icon in your system tray
- **Try restarting everything:**
  ```bash
  docker-compose down
  docker-compose up --build -d
  ```

### "I can't access the websites"
- **Wait a bit longer** - Sometimes it takes 2-3 minutes for everything to start
- **Check if something else is using the ports** - Close other development tools
- **Try different ports** - Edit the `docker-compose.yml` file to use different port numbers

### "No audio clips found"
- **Run the data loading command:**
  ```bash
  docker-compose exec api python seed_data.py
  ```

### "The audio won't play"
- **Check your internet connection** - The sample audio files are hosted online
- **Try a different browser** - Some browsers block audio playback
- **Check browser permissions** - Allow audio playback when prompted

## 🌍 Putting Your App Online (Deployment)

### Easy Options for Non-Technical Users:

**Railway (Recommended)**
1. Create an account at [railway.app](https://railway.app)
2. Connect your GitHub repository
3. Railway automatically deploys your app
4. Get a public URL like `https://your-app.railway.app`

**Render**
1. Create an account at [render.com](https://render.com)
2. Connect your GitHub repository
3. Follow the setup wizard
4. Get a public URL like `https://your-app.onrender.com`

### What Deployment Means:
Instead of your app only working on your computer, deployment puts it on the internet so anyone can use it from anywhere in the world.

## 🎬 Creating a Demo Video

### What to Show (5 minutes total):

**Introduction (30 seconds):**
- "I built a backend service for streaming audio clips"
- Show the project folder structure

**API Demo (2 minutes):**
- Open `http://localhost:8000/docs` - show the API documentation
- Test the endpoints in your browser
- Show how play counts increase when you stream clips

**Monitoring Demo (1 minute):**
- Open Grafana dashboard
- Show the real-time graphs and metrics
- Explain what each graph means

**Code Overview (1 minute):**
- Briefly show the main files and explain their purpose
- Highlight the clean organization

**Live Demo (30 seconds):**
- Show the deployed version working online
- Demonstrate the same functionality

### Tools for Recording:
- **Loom** (easiest) - Records your screen and voice automatically
- **OBS Studio** (free) - More professional recording
- **Zoom** - Can record your screen sharing

## 🎯 What Makes This Project Special

### For Non-Technical People:
- **Complete working system** - Not just code, but a real application you can use
- **Professional monitoring** - Like having a dashboard in your car
- **Easy setup** - One command gets everything running
- **Real audio playback** - You can actually listen to the clips
- **Beautiful documentation** - Easy to understand what everything does

### For Technical People:
- **Clean architecture** - Proper separation of concerns
- **Comprehensive testing** - Unit tests, integration tests, load testing
- **Production-ready** - Error handling, logging, monitoring
- **Multiple deployment options** - Railway, Render, Vercel, AWS
- **Industry best practices** - Docker, CI/CD, infrastructure as code

## 📚 Learning Resources

### If You Want to Learn More:

**For Beginners:**
- [What is an API?](https://www.freecodecamp.org/news/what-is-an-api-in-english-please-b880a3214a82/)
- [What is Docker?](https://www.docker.com/resources/what-container/)
- [What is a Database?](https://www.oracle.com/database/what-is-database/)

**For Developers:**
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Tutorial](https://www.postgresql.org/docs/current/tutorial.html)
- [Docker Compose Guide](https://docs.docker.com/compose/)

## 🆘 Getting Help

### If You're Stuck:
1. **Check the troubleshooting section above**
2. **Look at the error messages** - they often tell you exactly what's wrong
3. **Try the automatic test script** - `python simple_test.py`
4. **Start fresh** - Sometimes it's easier to delete everything and start over

### Common Error Messages and What They Mean:

**"Connection refused"** - The service isn't running yet, wait a bit longer
**"Port already in use"** - Something else is using the same port, restart your computer
**"Permission denied"** - Run your terminal as administrator
**"Module not found"** - Install the required software dependencies

## 🎉 Success Indicators

### You Know Everything is Working When:
- ✅ You can visit `http://localhost:8000/docs` and see the API documentation
- ✅ You can visit `http://localhost:8000/clips` and see 6 audio clips
- ✅ You can visit `http://localhost:3000` and see monitoring graphs
- ✅ The automatic test script shows all tests passing
- ✅ You can click on audio clips and actually hear them play