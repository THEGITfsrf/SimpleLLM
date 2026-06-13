from flask import Flask, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/multiplier')
def multiplier():
    import random
    result = round(random.uniform(0.8, 1.5), 2)
    return str(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
