import firebase_admin
from firebase_admin import credentials, firestore, db
from dotenv import load_dotenv
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

cred = credentials.Certificate(
    "./creds.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "stevens-games.firebaseapp.com"
})
load_dotenv()
rightPassword = os.getenv('PASSWORD')
# # Auburn Kebabs


@app.route("/ak", methods=["GET"])
def auburnkebabs():
    return getTeamGames("AUBURN KEBABS")
# NewJeans Elite


@app.route("/nje")
def newjeanselite():
    return getTeamGames("NEWJEANS ELITE")
# LeTeam


@app.route("/lt")
def leteam():
    return getTeamGames("LETEAM")


@app.route("/checkpassword/<password>", methods=["GET"])
def checkPassword(password):
    return password == rightPassword


@app.route("/game/<game_id>", methods=["GET"])
def get_game(game_id):
    try:
        db = firestore.client()
        # Fetch the game document from the "games" collection by its ID
        game_ref = db.collection("games").document(game_id)
        game_doc = game_ref.get()
        if not game_doc.exists:
            return jsonify({"error": "Game not found"}), 404
        # Convert the game document to a dictionary
        game_data = game_doc.to_dict()
        team1_doc = db.collection("teams").document(
            game_data["t1_id"]).get()
        team2_doc = db.collection("teams").document(
            game_data["t2_id"]).get()
        team1_name = team1_doc.to_dict().get(
            "name") if team1_doc.exists else "Unknown Team 1"
        team2_name = team2_doc.to_dict().get(
            "name") if team2_doc.exists else "Unknown Team 2"
        # Create a response structure
        response_data = {
            "g_date": game_data["g_date"],  # Firestore timestamp
            "team1": team1_name,
            "team2": team2_name,
            "youtube_link": game_data["youtube_link"]
        }
        print(response_data)
        return jsonify({"game": response_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/getteams", methods=["GET"])
def get_all_teams():
    try:
        db = firestore.client()
        # Fetch all games in one query
        teams_query = db.collection("teams").order_by(
            "name", direction=firestore.firestore.Query.ASCENDING).stream()

        teams = []

        for team in teams_query:
            team_data = team.to_dict()
            teams.append(team_data["name"])

        return jsonify({"games": teams})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# # Homepage all games


@app.route("/", methods=["GET"])
def allGames():
    try:
        db = firestore.client()

        # Fetch all games in one query
        games_query = db.collection("games").order_by(
            "g_date", direction=firestore.firestore.Query.DESCENDING).stream()

        # Prepare a dictionary to batch fetch all team documents needed
        team_ids = set()
        games_data = []

        # Gather game data and collect unique team IDs
        for game_doc in games_query:
            game_data = game_doc.to_dict()
            game_data["game_id"] = game_doc.id
            games_data.append(game_data)
            team_ids.update([game_data["t1_id"], game_data["t2_id"]])

        # Batch fetch all team documents
        team_docs = db.get_all([db.collection("teams").document(
            team_id) for team_id in team_ids])  # type: ignore
        team_map = {team_doc.id: team_doc.to_dict()
                    for team_doc in team_docs if team_doc.exists}

        # Process each game with the fetched team names
        games_list = []
        for game_data in games_data:
            team1_name = team_map.get(game_data["t1_id"], {}).get(
                "name", "Unknown Team 1")
            team2_name = team_map.get(game_data["t2_id"], {}).get(
                "name", "Unknown Team 2")
            games_list.append({
                "game_id": game_data["game_id"],
                "team1": team1_name,
                "team2": team2_name,
                "date": game_data["g_date"],
                "youtube_link": game_data["youtube_link"]
            })

        return jsonify({"games": games_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Function to get games for specific teams


def getTeamGames(team):
    try:
        db = firestore.client()

        # Step 1: Get the team document to retrieve the team ID
        team_docs = db.collection("teams").where(
            "name", "==", team).limit(1).get()
        if not team_docs:
            return jsonify({"error": "Team not found"}), 404
        team_id = team_docs[0].id

        # Step 2: Fetch all games where this team is the first team in a single query
        games_query = db.collection("games").where("t1_id", "==", team_id).order_by(
            "g_date", direction=firestore.firestore.Query.DESCENDING).stream()

        # Step 3: Gather all unique `t2_id`s to batch-fetch team2 documents in one request
        game_data_list = []
        team2_ids = set()

        for game_doc in games_query:
            game_data = game_doc.to_dict()
            game_data["game_id"] = game_doc.id
            game_data_list.append(game_data)
            team2_ids.add(game_data["t2_id"])

        # Step 4: Batch fetch all team2 documents
        team2_docs = db.get_all(
            [db.collection("teams").document(team_id) for team_id in team2_ids])
        team2_map = {team_doc.id: team_doc.to_dict().get(
            "name", "Unknown Team 2") for team_doc in team2_docs if team_doc.exists}

        # Step 5: Build the response with team names
        games_list = []
        for game_data in game_data_list:
            games_list.append({
                "game_id": game_data["game_id"],
                "team1": team,
                "team2": team2_map.get(game_data["t2_id"], "Unknown Team 2"),
                "date": game_data["g_date"],
                "youtube_link": game_data["youtube_link"]
            })

        return jsonify({"games": games_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Function to add games


@app.route("/addgame", methods=["POST"])
def add_game():
    # Extract data from the JSON request body
    data = request.get_json()

    team1_name = data.get("team1_name")
    team2_name = data.get("team2_name")
    game_date = data.get("game_date")
    youtube_link = data.get("youtube_link")
    try:
        db = firestore.client()

        team1_name = team1_name.upper()
        team2_name = team2_name.upper()

        def get_or_create_team_id(team_name):
            team_ref = db.collection("teams").where(
                "name", "==", team_name).limit(1).stream()
            team_id = None
            for team in team_ref:
                team_id = team.id  # If the team exists, get its document ID

            if team_id is None:
                # If team doesn't exist, add it to the teams collection
                new_team_ref = db.collection("teams").add({"name": team_name})
                # Get the document ID of the newly created team
                team_id = new_team_ref[1].id

            return team_id

        # Fetch or create team IDs for team1 and team2
        team1_id = get_or_create_team_id(team1_name)
        team2_id = get_or_create_team_id(team2_name)

        # Parse the date from dd/mm/yyyy to a Firestore-compatible datetime object
        game_datetime = datetime.strptime(game_date, "%Y-%m-%d")

        youtube_link = youtube_link.replace("watch?v=", "embed/")

        # Prepare game data to push to "games" collection
        game_data = {
            "t1_id": team1_id,
            "t2_id": team2_id,
            "g_date": game_datetime,
            "youtube_link": youtube_link
        }

        # Add the new game to the "games" collection
        db.collection("games").add(game_data)
        return jsonify({"Game added!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
