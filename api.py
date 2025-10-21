import json
import pandas as pd
import numpy as np
import logging
from flask import Flask, request, jsonify, stream_with_context, Response, stream_template
from flask_cors import CORS
from asgiref.wsgi import WsgiToAsgi
from werkzeug.urls import url_parse
from preprocessing import AWS
from model_pipeline import run, run_streaming
app = Flask(__name__)
logging.basicConfig(filename="./consult.log", format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
'''
@app.route("/chat", methods=["POST"])
def chat():
    approach = request.json["approach"]
    
    referrer = str(request.referrer)
    if referrer == "None":
        return jsonify({"reject": referrer, "reason": "http status 403"}), 403
    elif url_parse(referrer).host + ":4200" == "localhost:4200":
        pass
    elif url_parse(referrer).host == "":
        pass
    else:
        return jsonify({"reject": referrer, "reason": "http status 403"}), 403
    
    try:
        r = run(request.json["history"], request.json["tk"])
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /chat")
        return jsonify({"error": str(e)}), 500
'''
@app.route("/chat1", methods=["POST"])
def chat1():
    history = request.json["history"]
    tk = request.json["tk"]
    condition = request.json["condition"]

    referrer = str(request.referrer)
    if referrer == "None":
        return jsonify({"reject": referrer, "reason": "http status 403"}), 403
    elif url_parse(referrer).host + ":4200" == "localhost:4200":
        pass
    elif url_parse(referrer).host == "":
        pass
    else:
        return jsonify({"reject": referrer, "reason": "http status 403"}), 403

    try:
        aws = AWS()
        results, sysmg, subject, other_subject, image_dict, condition, final_question = run_streaming(history, tk, condition)
        if sysmg != []:
            headers = {
                "Content-Type": "text/event-stream",
                "Cache_Control": "no-cache",
                "X_Accel_Beffering": "no"
            }
            return Response(aws.sonnect_streaming(results, sysmg, subject, other_subject, image_dict, condition, final_question), headers=headers)
        else:
            data_info = {"data_points": [], "subject": [], "other_subject": [], "image_dict": [], "condition": "None", "query_text": final_question}
            return jsonify(data_info)
    except Exception as e:
        logging.exception("Exception in /chat")
        return jsonify({"error": str(e)}), 500

#asgi_app = WsgiToAsgi(app)
if __name__ == "__main__":
    app.run(host = '0.0.0.0', debug = True, port = "6060")