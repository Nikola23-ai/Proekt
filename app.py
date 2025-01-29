from flask import Flask, jsonify, request
from pymongo.mongo_client import MongoClient
from models import UserSpending, UserInfo
from extensions import db
import requests

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users_vouchers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

# MongoDB setup
uri = "mongodb+srv://Nikola23:admin@cluster0.kqf5d.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# Create a new client and connect to the server
client = MongoClient(uri)
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

mongo_db = client['users_vouchers']  # Replace with your database name
mongo_collection = mongo_db['users_vouchers']  # Replace with your collection name

TELEGRAM_BOT_TOKEN = 'your_bot_token'
TELEGRAM_CHAT_ID = 'your_chat_id'


# Endpoint 1: Retrieve Total Spending by User
@app.route('/total_spent/<int:user_id>', methods=['GET'])
def total_spent(user_id):
    total = db.session.query(db.func.sum(UserSpending.money_spent)).filter_by(user_id=user_id).scalar()
    total = total or 0
    response = {
        'user_id': user_id,
        'total_spent': total
    }
    return jsonify(response), 200


# Endpoint 2: Calculate Average Spending by Age Ranges
@app.route('/average_spending_by_age', methods=['GET'])
def average_spending_by_age():
    age_ranges = [
        (18, 24),
        (25, 30),
        (31, 36),
        (37, 47),
        (48, None)
    ]
    results = {}
    for lower, upper in age_ranges:
        query = db.session.query(db.func.avg(UserSpending.money_spent))\
            .join(UserInfo, UserSpending.user_id == UserInfo.user_id)
        if upper:
            query = query.filter(UserInfo.age.between(lower, upper))
        else:
            query = query.filter(UserInfo.age >= lower)
        average = query.scalar() or 0
        results[f'{lower}-{upper or "Above"}'] = average

    message = f"Average Spending by Age Ranges:\n" + "\n".join(
        f"{range_}: {average:.2f}" for range_, average in results.items()
    )
    requests.post(
        f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
        data={'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    )

    return jsonify(results), 200


# Endpoint 3: Write User Data to MongoDB
@app.route('/write_to_mongodb', methods=['POST'])
def write_to_mongodb():
    try:
        for user in UserInfo.query.all():
            total_spending = db.session.query(db.func.sum(UserSpending.money_spent)).filter_by(user_id=user.user_id).scalar() or 0  # Default to 0 if no spending found

            if total_spending > 1000:
                mongo_collection.insert_one({
                    'user_id': user.user_id,
                    'total_spending': total_spending
                })

        return jsonify({'message': 'Data successfully written to MongoDB'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
