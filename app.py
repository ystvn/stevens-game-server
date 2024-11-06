from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, db
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

cred = credentials.Certificate('/etc/secrets/FIREBASE_CREDS.json')
firebase_admin.initialize_app(cred)

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


# # Homepage all games
@app.route("/", methods=["GET"])
def allGames():
    try:
        db = firestore.client()
        games_query = db.collection("games").order_by(
            "g_date", direction=firestore.firestore.Query.DESCENDING).stream()

        games_list = []

        for game_doc in games_query:
            game_data = game_doc.to_dict()

            team1_doc = db.collection("teams").document(
                game_data["t1_id"]).get()
            team2_doc = db.collection("teams").document(
                game_data["t2_id"]).get()

            team1_name = team1_doc.to_dict().get(
                "name") if team1_doc.exists else "Unknown Team 1"
            team2_name = team2_doc.to_dict().get(
                "name") if team2_doc.exists else "Unknown Team 2"

            games_list.append({
                "game_id": game_doc.id,
                "team1": team1_name,
                "team2": team2_name,
                "date": game_data['g_date'],
                "youtube_link": game_data['youtube_link']
            })

        return jsonify({"games": games_list})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Function to get games for specific teams


def getTeamGames(team):
    try:
        db = firestore.client()

        team_docs = db.collection("teams").where(
            "name", "==", team).limit(1).get()

        if not team_docs:
            return jsonify({"error": "Team not found"}), 404

        team_id = team_docs[0].id

        games_query = db.collection("games").where("t1_id", "==", team_id).order_by(
            "g_date", direction=firestore.firestore.Query.DESCENDING).stream()

        games_list = []

        for game_doc in games_query:
            game_data = game_doc.to_dict()

            team2_doc = db.collection("teams").document(
                game_data["t2_id"]).get()
            team2_name = team2_doc.to_dict().get(
                "name") if team2_doc.exists else "Unknown Team 2"

            games_list.append({
                "game_id": game_doc.id,
                "team1": team,
                "team2": team2_name,
                "date": game_data['g_date'],
                "youtube_link": game_data['youtube_link']
            })

        return jsonify({"games": games_list})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)

# def add_game(team1_name, team2_name, game_date, youtube_link):
#     db = firestore.client()
#     # Fetch team IDs from "teams" collection based on team names
#     team1_ref = db.collection("teams").where(
#         "name", "==", team1_name).limit(1).stream()
#     team2_ref = db.collection("teams").where(
#         "name", "==", team2_name).limit(1).stream()

#     team1_id = None
#     team2_id = None

#     for team in team1_ref:
#         team1_id = team.id  # Get the document ID (team ID) for team 1
#     for team in team2_ref:
#         team2_id = team.id  # Get the document ID (team ID) for team 2

#     # If either team is not found, raise an error
#     if not team1_id or not team2_id:
#         raise ValueError(f"Could not find one or both teams: {
#                          team1_name}, {team2_name}")

#     # Parse the date from dd/mm/yyyy to a Firestore-compatible datetime object
#     game_datetime = datetime.strptime(game_date, "%d/%m/%Y")

#     # Prepare game data to push to "games" collection
#     game_data = {
#         "t1_id": team1_id,
#         "t2_id": team2_id,
#         "g_date": game_datetime,
#         "youtube_link": youtube_link
#     }

#     # Add the new game to the "games" collection
#     db.collection("games").add(game_data)
#     print("Game successfully added to Firestore.")
