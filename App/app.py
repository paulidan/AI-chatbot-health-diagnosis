from flask import Flask, render_template, request,jsonify

from chat import get_response
from mainchat import parse_args, get_auth_string, new_session
from consultation import AmbiguousAnswerException
import consultation
import API
import constant

app = Flask(__name__)
app.config['message_counter'] = 0
 
@app.route("/")
def index_get():
    return render_template("base.html")

@app.post("/predict")
def predict():
    text = request.get_json().get("message")
    response = get_response(text)
    message = {"answer": response }
    message = {}
    response = "To get your diagnosis, send an empty message!"

    # Stage 1: Ask for age and gender 
    if (app.config['message_counter'] == 0):
        try:
            age, gender = consultation.read_patient_info_new(text)
            age = {'value':  age, 'unit': 'year'}

            app.config['age'] = age
            app.config['gender'] = gender
            app.config['message_counter']+=1

            auth_string = app.config['auth_string']
            patient = app.config['patient']

            # query for observation names and storing them
            app.config['titling'] = API.get_observation_titles(age, auth_string, patient, None)

            response = "Please describe your symptoms."
        except (AmbiguousAnswerException, ValueError) as e:
            response = "{} Could you please repeat?".format(e)
    # Stage 2: Ask for symptomps
    elif (app.config['message_counter'] == 1):
        age = app.config['age']
        gender = app.config['gender']
        auth_string = app.config['auth_string']

        case_id = app.config['patient']
        circumstances = app.config['circumstances']

        answ = API.parse(age, gender, text, auth_string, case_id, circumstances,
                                language_model=None)
        portion = answ.get('mentions', [])
        if text == " ":
            portion = None

        if portion:
            response = consultation.summarise_mentions(portion)
            app.config['report'].extend(portion)
            app.config['circumstances'].extend(consultation.id_complains(portion))

        # response = "Please describe your symptoms."
        report = app.config['report']
        print(f"Report: {report} \nPortion: {portion}")

        # empty message but got at least one complaint
        if app.config['report'] and portion is None:

            app.config['proof'] = API.statement_to_evidence(report)
            app.config['message_counter']+=1

            print(app.config['proof'])

            response = "Symptops acquired, send empty message"
    # Stage 3: Asking stupid questions
    elif (app.config['message_counter'] == 2):
        proof = app.config['proof']
        obs_value = None

        age = app.config['age']
        gender = app.config['gender']
        auth = app.config['auth_string']

        case_id = app.config['patient']
        answ = API.diagnosis_endpoint(proof, age, gender, case_id, auth,
                                        language_model=None)
        question_type = answ['question']
        app.config['diagnoses'] = diagnoses = answ['conditions']
        should_stop_now = answ['should_stop']

        if should_stop_now:
            app.config['triage'] = API.triage_endpoint(proof, age, gender, case_id,
                                                auth,
                                                language_model=None)
            app.config['message_counter']+=1                                    
        else:
            if question_type['type'] == 'single':
                # only single question type
                question_items = question_type['items']
                assert len(question_items) == 1  # this is a single question TO-DO Change to an if statement
                question_item = question_items[0]
                response = question_type['text']

                if not response:
                    response = "TO-DO"
                try:
                    obs_value = consultation.make_decision(text, constant.RESPONSE)
                except (AmbiguousAnswerException, ValueError) as e:
                    response = "Type yes, if you want to get your answer."

                if obs_value is not None:
                    app.config['new_evidence'].extend(API.question_to_evidence(
                        question_item, obs_value))
                    app.config['proof'].extend(app.config['new_evidence'])
            else:
                response = "Unfortunately group questions were not implemented yet..."
    # Stage 4: Print diagnosis
    elif (app.config['message_counter'] == 3):

        proof = app.config['proof']
        titling = app.config['titling']

        API.label_evidence(proof, titling)

        # printing all information about the patient.
        print()
        consultation.summarise_everything(proof)

        diagnosis_str = consultation.summarise_diagnoses(app.config['diagnoses'])
        triage_str = consultation.summarise_triage(app.config['triage'])

        response = diagnosis_str + "\n" + triage_str

    message = {"answer": response}
    return jsonify(message)

if __name__ == "__main__":

    args = parse_args()
    auth_string = get_auth_string(args.auth)
    patient = new_session()

    app.config["patient"] = patient
    app.config['auth_string'] = auth_string

    app.config['circumstances'] = []
    app.config['report'] = []

    app.config['new_evidence'] = []

    app.run(debug=True)